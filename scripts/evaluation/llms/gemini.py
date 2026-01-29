#!/usr/bin/env python3
"""
Google Gemini service for video analysis using LangGraph.
Implements a stateful workflow with video upload, processing, analysis, and cleanup.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import os
import logging
import time
import json
from typing import Dict, Optional, TypedDict, Annotated
from dotenv import load_dotenv

# LangChain and LangGraph imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
import google.generativeai as genai

from scripts.evaluation.llms.base import VideoLLMService
from scripts.evaluation.models import CommunityNoteOutput, VideoAnalysisResult
from scripts.evaluation.prompts import PromptTemplate

load_dotenv()
logger = logging.getLogger(__name__)


# Define the state schema for the LangGraph workflow
class VideoAnalysisState(TypedDict):
    """State for video analysis workflow."""

    video_path: str
    tweet_text: str
    author_name: str
    author_username: Optional[str]
    tweet_created_at: Optional[str]
    model_name: str

    # Workflow state
    video_file: Optional[any]  # Uploaded video file object
    video_file_name: Optional[str]  # File name for cleanup
    prompt: Optional[str]
    response_data: Optional[Dict]
    result: Optional[Dict]
    error: Optional[str]


class GeminiService(VideoLLMService):
    """Google Gemini service for video analysis using LangGraph workflow.

    Implements a stateful workflow with explicit nodes for:
    - Video upload
    - Processing wait
    - Analysis generation
    - Cleanup

    Supports multiple Gemini models:
    - gemini-2.5-flash (default)
    """

    def __init__(
        self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"
    ):
        """Initialize Gemini service with LangGraph workflow.

        Args:
            api_key: Google AI Studio API key (if None, loads from GEMINI_API_KEY env var)
            model_name: Gemini model to use
        """
        super().__init__(api_key)
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self._llm = None
        self._workflow = None

    def is_available(self) -> bool:
        """Check if Gemini API is available."""
        return bool(self.api_key)

    def _initialize(self):
        """Initialize LangChain model and configure Gemini API."""
        if self._llm is None:
            try:
                # Configure Gemini API
                genai.configure(api_key=self.api_key)

                # Initialize LangChain Gemini model with structured output
                self._llm = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=0.0,  # Deterministic for research
                ).with_structured_output(CommunityNoteOutput)

                logger.info(f"Initialized LangChain Gemini: {self.model_name}")
            except ImportError as e:
                raise ImportError(
                    f"Required libraries not installed: {e}\n"
                    "Install with: pip install langchain-google-genai langgraph"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Gemini: {e}")

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for video analysis."""

        # Define workflow nodes
        def upload_video(state: VideoAnalysisState) -> VideoAnalysisState:
            """Upload video to Gemini."""
            logger.info(f"Uploading video: {state['video_path']}")
            try:
                video_file = genai.upload_file(path=state["video_path"])
                state["video_file"] = video_file
                state["video_file_name"] = video_file.name
                logger.info(f"  ✓ Video uploaded: {video_file.name}")
            except Exception as e:
                state["error"] = f"Video upload failed: {e}"
                logger.error(state["error"])
            return state

        def wait_for_processing(state: VideoAnalysisState) -> VideoAnalysisState:
            """Wait for video processing to complete."""
            if state.get("error"):
                return state

            video_file = state["video_file"]
            logger.info("Waiting for video processing...")

            try:
                max_retries = 30  # 60 seconds timeout
                retries = 0

                while video_file.state.name == "PROCESSING" and retries < max_retries:
                    time.sleep(2)
                    video_file = genai.get_file(video_file.name)
                    retries += 1

                if video_file.state.name == "FAILED":
                    state["error"] = "Video processing failed"
                    logger.error(state["error"])
                elif video_file.state.name == "PROCESSING":
                    state["error"] = "Video processing timeout"
                    logger.error(state["error"])
                else:
                    state["video_file"] = video_file
                    logger.info("  ✓ Video processing complete")
            except Exception as e:
                state["error"] = f"Processing check failed: {e}"
                logger.error(state["error"])

            return state

        def analyze_video(state: VideoAnalysisState) -> VideoAnalysisState:
            """Generate analysis using LangChain Gemini."""
            if state.get("error"):
                return state

            try:
                # Generate prompt
                prompt = PromptTemplate.get_structured_prompt(
                    state["tweet_text"],
                    state["author_name"],
                    state["author_username"],
                    model_type="gemini",
                    tweet_created_at=state.get("tweet_created_at"),
                )
                state["prompt"] = prompt

                logger.info(f"Generating analysis with {state['model_name']}...")

                # Invoke LangChain model with video and prompt
                # Note: LangChain's Gemini integration requires special handling for video files
                # We'll use the genai model directly but structure with LangGraph workflow
                from langchain_core.messages import HumanMessage

                # Create message with video file reference
                message = HumanMessage(content=[{"type": "text", "text": prompt}])

                # For now, use genai directly for video + structured output
                # LangChain's video support is limited, so we use a hybrid approach
                model = genai.GenerativeModel(
                    state["model_name"],
                    generation_config={
                        "response_mime_type": "application/json",
                        "response_schema": {
                            "type": "object",
                            "properties": {
                                "predicted_label": {"type": "string"},
                                "is_misleading": {"type": "boolean"},
                                "summary": {"type": "string"},
                                "sources": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "reasons": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "confidence": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                },
                                "explanation": {"type": "string"},
                            },
                            "required": [
                                "predicted_label",
                                "is_misleading",
                                "summary",
                                "sources",
                                "reasons",
                                "confidence",
                            ],
                        },
                    },
                )

                response = model.generate_content([state["video_file"], prompt])
                response_data = json.loads(response.text)

                # Validate with Pydantic
                community_note = CommunityNoteOutput(**response_data)

                state["response_data"] = response_data
                state["result"] = VideoAnalysisResult(
                    success=True,
                    model=state["model_name"],
                    predicted_label=community_note.predicted_label,
                    is_misleading=community_note.is_misleading,
                    summary=community_note.summary,
                    sources=community_note.sources,
                    reasons=community_note.reasons,
                    confidence=community_note.confidence,
                    raw_response=response.text,
                ).model_dump()

                logger.info(
                    f"  ✓ Analysis complete (Misleading: {community_note.is_misleading})"
                )

            except Exception as e:
                state["error"] = f"Analysis failed: {e}"
                logger.error(state["error"])

            return state

        def cleanup(state: VideoAnalysisState) -> VideoAnalysisState:
            """Clean up uploaded video file."""
            if state.get("video_file_name"):
                try:
                    genai.delete_file(state["video_file_name"])
                    logger.info("  ✓ Cleaned up uploaded video")
                except Exception as e:
                    logger.warning(f"Cleanup warning: {e}")
            return state

        def handle_error(state: VideoAnalysisState) -> VideoAnalysisState:
            """Handle errors and create error result."""
            if not state.get("result"):
                state["result"] = VideoAnalysisResult(
                    success=False,
                    error=state.get("error", "Unknown error"),
                    model=state["model_name"],
                ).model_dump()
            return state

        # Build the graph
        workflow = StateGraph(VideoAnalysisState)

        # Add nodes
        workflow.add_node("upload", upload_video)
        workflow.add_node("wait_processing", wait_for_processing)
        workflow.add_node("analyze", analyze_video)
        workflow.add_node("cleanup", cleanup)
        workflow.add_node("error", handle_error)

        # Define edges with conditional routing
        workflow.set_entry_point("upload")

        # After upload, check for errors
        workflow.add_conditional_edges(
            "upload", lambda state: "error" if state.get("error") else "wait_processing"
        )

        # After processing, check for errors
        workflow.add_conditional_edges(
            "wait_processing",
            lambda state: "error" if state.get("error") else "analyze",
        )

        # After analysis, always cleanup
        workflow.add_conditional_edges(
            "analyze", lambda state: "error" if state.get("error") else "cleanup"
        )

        # Cleanup and error both end
        workflow.add_edge("cleanup", END)
        workflow.add_edge("error", "cleanup")

        return workflow.compile()

    def analyze_video(
        self,
        video_path: str,
        tweet_text: str,
        author_name: str,
        author_username: Optional[str] = None,
        tweet_created_at: Optional[str] = None,
    ) -> Dict:
        """
        Analyze video using LangGraph workflow with Gemini.

        The workflow consists of:
        1. Upload video to Gemini
        2. Wait for processing
        3. Generate analysis with structured output
        4. Cleanup uploaded file

        Args:
            video_path: Path to the video file
            tweet_text: Text of the tweet
            author_name: Name of the tweet author
            author_username: Username of the tweet author
            tweet_created_at: Creation time of the tweet (optional)

        Returns:
            Dictionary with analysis results conforming to VideoAnalysisResult
        """
        if not self.is_available():
            return VideoAnalysisResult(
                success=False,
                error="Gemini API key not configured",
                model=self.model_name,
            ).model_dump()

        try:
            self._initialize()

            # Build workflow (cached after first build)
            if self._workflow is None:
                self._workflow = self._build_workflow()

            # Create initial state
            initial_state: VideoAnalysisState = {
                "video_path": video_path,
                "tweet_text": tweet_text,
                "author_name": author_name,
                "author_username": author_username,
                "tweet_created_at": tweet_created_at,
                "model_name": self.model_name,
                "video_file": None,
                "video_file_name": None,
                "prompt": None,
                "response_data": None,
                "result": None,
                "error": None,
            }

            # Execute workflow
            logger.info(f"Executing LangGraph workflow for video analysis...")
            final_state = self._workflow.invoke(initial_state)

            # Return result from final state
            if final_state.get("result"):
                return final_state["result"]
            else:
                return VideoAnalysisResult(
                    success=False,
                    error=final_state.get("error", "Unknown workflow error"),
                    model=self.model_name,
                ).model_dump()

        except Exception as e:
            logger.error(f"Error in LangGraph workflow: {e}")
            return VideoAnalysisResult(
                success=False,
                error=str(e),
                model=self.model_name,
            ).model_dump()


if __name__ == "__main__":
    # Test Gemini service with LangGraph
    print("Testing Gemini Service (LangGraph Implementation)")
    print("=" * 70)

    # Test default model
    service = GeminiService()
    print(f"Default Model: {service.model_name}")
    print(f"Gemini Service available: {service.is_available()}")
    print(f"Using LangGraph workflow: ✓")

    # Test other models
    print("\nSupported Gemini Models:")
    models = ["gemini-1.5-pro", "gemini-2.0-flash-exp", "gemini-exp-1206"]
    for model in models:
        service = GeminiService(model_name=model)
        print(f"  - {model} (LangGraph workflow)")

    if not service.is_available():
        print("\nTo enable Gemini service, set environment variable:")
        print("  GEMINI_API_KEY=your_key")

    print("\nWorkflow Nodes:")
    print("  1. upload        - Upload video to Gemini")
    print("  2. wait_processing - Wait for video processing")
    print("  3. analyze       - Generate analysis with structured output")
    print("  4. cleanup       - Delete uploaded video file")
    print("  5. error         - Handle errors gracefully")

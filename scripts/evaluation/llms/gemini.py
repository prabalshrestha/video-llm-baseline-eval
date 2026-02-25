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
from typing import Dict, Optional, TypedDict, TYPE_CHECKING
from dotenv import load_dotenv

# Lazy imports to avoid segfault issues with langchain packages
# These will be imported only when the service is actually used
if TYPE_CHECKING:
    from langgraph.graph import StateGraph
    from google import genai
    from google.genai import types as genai_types

from scripts.evaluation.llms.base import VideoLLMService
from scripts.evaluation.models import CommunityNoteOutput, VideoAnalysisResult
from scripts.evaluation.prompts import PromptTemplate

load_dotenv()
logger = logging.getLogger(__name__)

# Models that support extended thinking; thought parts are extracted and stored
# in VideoAnalysisResult.thought_summary when these models are used.
_THINKING_MODELS: frozenset = frozenset({"gemini-3-pro-preview"})


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
    - gemini-3-flash-preview (default)
    - gemini-3-pro-preview
    - gemini-2.5-flash
    - gemini-2.5-pro
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3-flash-preview",
        use_grounding: bool = False,
    ):
        """Initialize Gemini service with LangGraph workflow.

        Args:
            api_key: Google AI Studio API key (if None, loads from GEMINI_API_KEY env var)
            model_name: Gemini model to use
            use_grounding: Enable Google Search grounding for real-time web context
        """
        super().__init__(api_key)
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.use_grounding = use_grounding
        self._client = None
        self._workflow = None

    def is_available(self) -> bool:
        """Check if Gemini API is available."""
        return bool(self.api_key)

    def _initialize(self):
        """Initialize Google GenAI client."""
        if self._client is None:
            try:
                from google import genai

                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized Google GenAI client: {self.model_name}")
            except ImportError as e:
                raise ImportError(
                    f"Required libraries not installed: {e}\n"
                    "Install with: pip install google-genai langgraph"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Gemini: {e}")

    def _build_workflow(self):
        """Build the LangGraph workflow for video analysis."""
        from langgraph.graph import StateGraph, END
        from google.genai import types as genai_types

        def upload_video(state: VideoAnalysisState) -> VideoAnalysisState:
            """Upload video to Gemini Files API."""
            logger.info(f"Uploading video: {state['video_path']}")
            try:
                video_file = self._client.files.upload(file=state["video_path"])
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

                def _state_name(f) -> str:
                    s = f.state
                    return s.name if hasattr(s, "name") else str(s)

                while _state_name(video_file) == "PROCESSING" and retries < max_retries:
                    time.sleep(2)
                    video_file = self._client.files.get(name=video_file.name)
                    retries += 1

                state_name = _state_name(video_file)
                if state_name == "FAILED":
                    state["error"] = "Video processing failed"
                    logger.error(state["error"])
                elif state_name == "PROCESSING":
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
            """Generate grounded analysis using Google Search tool."""
            if state.get("error"):
                return state

            try:
                prompt = PromptTemplate.get_structured_prompt(
                    state["tweet_text"],
                    state["author_name"],
                    state["author_username"],
                    model_type="gemini",
                    tweet_created_at=state.get("tweet_created_at"),
                )
                state["prompt"] = prompt

                is_thinking = state["model_name"] in _THINKING_MODELS
                labels = []
                if self.use_grounding:
                    labels.append("grounding=ON")
                if is_thinking:
                    labels.append("thinking=ON")
                logger.info(
                    f"Generating analysis with {state['model_name']}"
                    + (f" ({', '.join(labels)})" if labels else "") + "..."
                )

                tools = (
                    [genai_types.Tool(google_search=genai_types.GoogleSearch())]
                    if self.use_grounding
                    else None
                )
                thinking_config = (
                    genai_types.ThinkingConfig(include_thoughts=True)
                    if is_thinking
                    else None
                )

                response = self._client.models.generate_content(
                    model=state["model_name"],
                    contents=[state["video_file"], prompt],
                    config=genai_types.GenerateContentConfig(
                        temperature=0.0,
                        tools=tools,
                        thinking_config=thinking_config,
                        response_mime_type="application/json",
                        response_schema=CommunityNoteOutput,
                    ),
                )

                # Extract thought summary from thinking-capable models
                thought_summary: Optional[str] = None
                if is_thinking and response.candidates:
                    thought_parts = [
                        part.text
                        for part in response.candidates[0].content.parts
                        if getattr(part, "thought", False) and part.text
                    ]
                    if thought_parts:
                        thought_summary = "\n".join(thought_parts)
                        logger.info(
                            f"  ✓ Thought summary captured ({len(thought_summary)} chars)"
                        )

                # response.parsed is automatically deserialized into CommunityNoteOutput
                community_note: CommunityNoteOutput = response.parsed
                raw_text = response.text

                state["response_data"] = community_note.model_dump()
                state["result"] = VideoAnalysisResult(
                    success=True,
                    model=state["model_name"],
                    predicted_label=community_note.predicted_label,
                    is_misleading=community_note.is_misleading,
                    summary=community_note.summary,
                    sources=community_note.sources,
                    misleading_tags=community_note.misleading_tags,
                    confidence=community_note.confidence,
                    raw_response=raw_text,
                    thought_summary=thought_summary,
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
                    self._client.files.delete(name=state["video_file_name"])
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

        workflow.add_node("upload", upload_video)
        workflow.add_node("wait_processing", wait_for_processing)
        workflow.add_node("analyze", analyze_video)
        workflow.add_node("cleanup", cleanup)
        workflow.add_node("error", handle_error)

        workflow.set_entry_point("upload")

        workflow.add_conditional_edges(
            "upload", lambda state: "error" if state.get("error") else "wait_processing"
        )
        workflow.add_conditional_edges(
            "wait_processing",
            lambda state: "error" if state.get("error") else "analyze",
        )
        workflow.add_conditional_edges(
            "analyze", lambda state: "error" if state.get("error") else "cleanup"
        )

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
        1. Upload video to Gemini Files API
        2. Wait for processing
        3. Generate grounded analysis (Google Search tool enabled)
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
    import argparse

    parser = argparse.ArgumentParser(description="Gemini video analysis service")
    parser.add_argument(
        "--model",
        default="gemini-3-flash-preview",
        help="Gemini model name (default: gemini-3-flash-preview)",
    )
    parser.add_argument(
        "--grounding",
        action="store_true",
        default=False,
        help="Enable Google Search grounding for real-time web context",
    )
    args = parser.parse_args()

    print("Testing Gemini Service (google-genai SDK)")
    print("=" * 70)

    service = GeminiService(model_name=args.model, use_grounding=args.grounding)
    print(f"Model:        {service.model_name}")
    print(f"Grounding:    {'enabled' if service.use_grounding else 'disabled'}")
    print(f"Available:    {service.is_available()}")

    if not service.is_available():
        print("\nTo enable Gemini service, set environment variable:")
        print("  GEMINI_API_KEY=your_key")

    print("\nWorkflow Nodes:")
    print("  1. upload          - Upload video to Gemini Files API")
    print("  2. wait_processing - Wait for video processing")
    print("  3. analyze         - Structured JSON analysis (grounding optional)")
    print("  4. cleanup         - Delete uploaded video file")
    print("  5. error           - Handle errors gracefully")

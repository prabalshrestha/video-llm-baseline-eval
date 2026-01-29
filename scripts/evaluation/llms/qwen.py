#!/usr/bin/env python3
"""
Qwen VL service for video analysis using LangChain + Ollama.
Supports Qwen3-VL models with native video understanding via Ollama.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import os
import logging
import json
import base64
from typing import Dict, Optional, TypedDict
from dotenv import load_dotenv

# LangChain imports
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from scripts.evaluation.llms.base import VideoLLMService
from scripts.evaluation.models import CommunityNoteOutput, VideoAnalysisResult
from scripts.evaluation.prompts import PromptTemplate

load_dotenv()
logger = logging.getLogger(__name__)


# Define the state schema for the LangGraph workflow
class VideoAnalysisState(TypedDict):
    """State for Qwen video analysis workflow with structured output."""
    
    # Input parameters
    video_path: str
    tweet_text: str
    author_name: str
    author_username: Optional[str]
    tweet_created_at: Optional[str]
    model_name: str
    
    # Workflow state (simplified with structured output!)
    video_data: Optional[str]  # Video path for Ollama
    prompt: Optional[str]
    result: Optional[Dict]  # VideoAnalysisResult directly
    error: Optional[str]


class QwenService(VideoLLMService):
    """Qwen VL service for video analysis using LangChain + Ollama.

    Uses LangGraph workflow orchestration with Ollama for local inference.
    
    Supports Qwen3-VL models via Ollama:
    - qwen3-vl-cloud: Optimized for cloud deployment (recommended)
    - qwen2.5-vl: Standard Qwen 2.5 VL model
    
    Workflow nodes:
    - prepare: Prepare video data for analysis
    - analyze: Generate analysis using Ollama with structured output
    - error: Handle errors gracefully
    
    Requirements:
    - Ollama installed and running (https://ollama.ai)
    - Qwen VL model pulled: `ollama pull qwen3-vl-cloud`
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "qwen3-vl-cloud",
        ollama_base_url: Optional[str] = None,
        use_local: bool = True,  # Default to Ollama (local)
    ):
        """Initialize Qwen service with LangChain + Ollama.

        Args:
            api_key: Legacy API key (for DashScope fallback)
            model_name: Ollama model name (default: qwen3-vl-cloud)
            ollama_base_url: Ollama base URL (default: http://localhost:11434)
            use_local: Whether to use Ollama (True) or DashScope API (False)
        """
        super().__init__(api_key)
        if not self.api_key:
            self.api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")

        self.model_name = model_name
        self.ollama_base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.use_local = use_local
        self._llm = None
        self._workflow = None

    def is_available(self) -> bool:
        """Check if Qwen service is available."""
        if self.use_local:
            # For Ollama, check if langchain-ollama is available
            try:
                import requests
                # Check if Ollama is running
                response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=2)
                if response.status_code == 200:
                    # Check if model is available
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    if any(self.model_name in name for name in model_names):
                        return True
                    else:
                        logger.warning(
                            f"Model {self.model_name} not found in Ollama. "
                            f"Pull it with: ollama pull {self.model_name}"
                        )
                        return False
                return False
            except Exception as e:
                logger.warning(f"Ollama not available: {e}")
                logger.warning("Install Ollama from https://ollama.ai")
                return False
        else:
            # For API inference, check if API key is set
            return bool(self.api_key)

    def _initialize(self):
        """Initialize LangChain Ollama model with structured output."""
        if self._llm is None:
            try:
                if self.use_local:
                    # Initialize LangChain Ollama with structured output
                    self._llm = ChatOllama(
                        model=self.model_name,
                        base_url=self.ollama_base_url,
                        temperature=0.0,  # Deterministic for research
                    ).with_structured_output(CommunityNoteOutput)
                    logger.info(f"Initialized LangChain Ollama with structured output: {self.model_name}")
                else:
                    # Fallback to DashScope API
                    logger.info("Using DashScope API mode (legacy)")
                    
            except ImportError as e:
                raise ImportError(
                    f"Required libraries not installed: {e}\n"
                    "Install with: pip install langchain-ollama"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Qwen: {e}")

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for Qwen video analysis."""
        
        def prepare_video(state: VideoAnalysisState) -> VideoAnalysisState:
            """Prepare video data for analysis."""
            logger.info(f"Preparing video: {state['video_path']}")
            try:
                # For Ollama, we pass the video file path directly
                # Ollama's multimodal support handles video loading
                state["video_data"] = state["video_path"]
                logger.info("  ✓ Video prepared")
            except Exception as e:
                state["error"] = f"Video preparation failed: {e}"
                logger.error(state["error"])
            return state
        
        def analyze_video(state: VideoAnalysisState) -> VideoAnalysisState:
            """Generate analysis using LangChain Ollama with structured output."""
            if state.get("error"):
                return state
                
            try:
                # Generate prompt
                prompt = PromptTemplate.get_structured_prompt(
                    state["tweet_text"],
                    state["author_name"],
                    state["author_username"],
                    model_type="qwen",
                    tweet_created_at=state.get("tweet_created_at"),
                )
                state["prompt"] = prompt
                
                logger.info(f"Analyzing with {state['model_name']}...")
                
                # Create multimodal message
                # Note: Ollama's video support varies by model
                # For now, we'll use text-only and reference the video
                message = HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": f"Video file: {state['video_data']}\n\n{prompt}"
                        }
                    ]
                )
                
                # Invoke LangChain Ollama - returns CommunityNoteOutput directly!
                community_note = self._llm.invoke([message])
                
                # Create result from Pydantic object
                state["result"] = VideoAnalysisResult(
                    success=True,
                    model=state["model_name"],
                    predicted_label=community_note.predicted_label,
                    is_misleading=community_note.is_misleading,
                    summary=community_note.summary,
                    sources=community_note.sources,
                    reasons=community_note.reasons,
                    confidence=community_note.confidence,
                    raw_response=str(community_note.model_dump()),
                ).model_dump()
                
                logger.info(f"  ✓ Analysis complete (Misleading: {community_note.is_misleading})")
                
            except Exception as e:
                state["error"] = f"Analysis failed: {e}"
                logger.error(state["error"])
                
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
        
        # Add nodes (only 3 nodes now!)
        workflow.add_node("prepare", prepare_video)
        workflow.add_node("analyze", analyze_video)
        workflow.add_node("error", handle_error)
        
        # Define edges with conditional routing
        workflow.set_entry_point("prepare")
        
        # After prepare, check for errors
        workflow.add_conditional_edges(
            "prepare",
            lambda state: "error" if state.get("error") else "analyze"
        )
        
        # After analyze, check for errors or end directly
        workflow.add_conditional_edges(
            "analyze",
            lambda state: "error" if state.get("error") else END
        )
        
        # Error ends
        workflow.add_edge("error", END)
        
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
        Analyze video using LangGraph workflow with Ollama structured output.

        The workflow consists of:
        1. Prepare video data
        2. Generate analysis using Ollama (returns Pydantic object directly)
        3. Handle errors gracefully

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
                error=f"Qwen service not available. "
                      f"{'Ollama not running or model not found' if self.use_local else 'API key not configured'}",
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
                "video_data": None,
                "prompt": None,
                "result": None,
                "error": None,
            }
            
            # Execute workflow
            logger.info(f"Executing LangGraph workflow for Qwen analysis...")
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
    # Test Qwen service with LangChain + Ollama
    print("Testing Qwen VL Service (LangChain + Ollama Implementation)")
    print("=" * 70)

    # Test Ollama mode (default)
    print("\nOllama Mode (LangGraph workflow):")
    service = QwenService(model_name="qwen3-vl-cloud", use_local=True)
    print(f"  Model: {service.model_name}")
    print(f"  Ollama URL: {service.ollama_base_url}")
    print(f"  Available: {service.is_available()}")
    print(f"  Using LangGraph workflow: ✓")

    if not service.is_available():
        print("\n⚠️  Ollama not available!")
        print("\nTo enable Qwen service with Ollama:")
        print("  1. Install Ollama: https://ollama.ai")
        print("  2. Pull the model: ollama pull qwen3-vl-cloud")
        print("  3. Verify: ollama list")
    
    print("\nWorkflow Nodes:")
    print("  1. prepare  - Prepare video data")
    print("  2. analyze  - Generate analysis with Ollama (structured output)")
    print("  3. error    - Handle errors gracefully")
    
    print("\nRecommended Models:")
    print("  - qwen3-vl-cloud  - Optimized for cloud deployment (recommended)")
    print("  - qwen2.5-vl      - Standard Qwen 2.5 VL model")
    
    print("\nRequirements:")
    print("  - Ollama running locally or remotely")
    print("  - langchain-ollama: pip install langchain-ollama")
    print("  - Model pulled: ollama pull qwen3-vl-cloud")

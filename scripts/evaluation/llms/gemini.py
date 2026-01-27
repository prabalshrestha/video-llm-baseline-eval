#!/usr/bin/env python3
"""
Google Gemini 1.5 Pro service for video analysis.
Uses structured output with Pydantic models.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import os
import logging
import time
from typing import Dict, Optional
from dotenv import load_dotenv

from scripts.evaluation.llms.base import VideoLLMService
from scripts.evaluation.models import CommunityNoteOutput, VideoAnalysisResult
from scripts.evaluation.prompts import PromptTemplate

load_dotenv()
logger = logging.getLogger(__name__)


class GeminiService(VideoLLMService):
    """Google Gemini service for video analysis with structured output.

    Supports multiple Gemini models:
    - gemini-1.5-pro (default) - Original workhorse model
    - gemini-2.5-flash - Best price-performance (stable)
    - gemini-2.5-pro - Advanced thinking model
    """

    def __init__(
        self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-pro"
    ):
        """Initialize Gemini service.

        Args:
            api_key: Google AI Studio API key (if None, loads from GEMINI_API_KEY env var)
            model_name: Gemini model to use (gemini-1.5-pro, gemini-2.0-flash-exp, gemini-exp-1206)
        """
        super().__init__(api_key)
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self._genai = None
        self._model = None

    def is_available(self) -> bool:
        """Check if Gemini API is available."""
        return bool(self.api_key)

    def _initialize(self):
        """Lazy initialization of Gemini client."""
        if self._model is None:
            try:
                import google.generativeai as genai

                self._genai = genai
                genai.configure(api_key=self.api_key)

                # Configure model with structured output schema
                self._model = genai.GenerativeModel(
                    self.model_name,
                    generation_config={
                        "response_mime_type": "application/json",
                        "response_schema": {
                            "type": "object",
                            "properties": {
                                "predicted_label": {"type": "string"},
                                "is_misleading": {"type": "boolean"},
                                "predicted_label": {"type": "string"},
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
                                "predicted_label",
                                "summary",
                                "sources",
                                "reasons",
                                "confidence",
                            ],
                        },
                    },
                )
                logger.info(
                    f"Initialized Gemini model: {self.model_name} with structured output"
                )
            except ImportError:
                raise ImportError(
                    "google-generativeai library not installed. "
                    "Install with: pip install google-generativeai"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Gemini: {e}")

    def analyze_video(
        self,
        video_path: str,
        tweet_text: str,
        author_name: str,
        author_username: Optional[str] = None,
        tweet_created_at: Optional[str] = None,
    ) -> Dict:
        """
        Analyze video using Gemini 1.5 Pro with structured output.

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

            # Upload video file
            logger.info(f"Uploading video to Gemini: {video_path}")
            video_file = self._genai.upload_file(path=video_path)

            # Wait for processing
            while video_file.state.name == "PROCESSING":
                logger.info("  Waiting for video processing...")
                time.sleep(2)
                video_file = self._genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                return VideoAnalysisResult(
                    success=False,
                    error="Video processing failed",
                    model=self.model_name,
                ).model_dump()

            # Generate prompt using centralized template
            prompt = PromptTemplate.get_structured_prompt(
                tweet_text,
                author_name,
                author_username,
                model_type="gemini",
                tweet_created_at=tweet_created_at,
            )

            # Generate response
            logger.info(f"Generating response with {self.model_name}...")
            response = self._model.generate_content([video_file, prompt])

            # Parse structured JSON response
            import json

            response_data = json.loads(response.text)

            # Validate with Pydantic model
            community_note = CommunityNoteOutput(**response_data)

            result = VideoAnalysisResult(
                success=True,
                model=self.model_name,
                predicted_label=community_note.predicted_label,
                is_misleading=community_note.is_misleading,
                summary=community_note.summary,
                sources=community_note.sources,
                reasons=community_note.reasons,
                confidence=community_note.confidence,
                raw_response=response.text,
            )

            # Clean up uploaded file
            try:
                self._genai.delete_file(video_file.name)
            except:
                pass

            logger.info(
                f"  ✓ Analysis complete (Misleading: {community_note.is_misleading})"
            )
            return result.model_dump()

        except Exception as e:
            logger.error(f"Error analyzing video with Gemini: {e}")
            return VideoAnalysisResult(
                success=False,
                error=str(e),
                model=self.model_name,
            ).model_dump()


if __name__ == "__main__":
    # Test Gemini service
    print("Testing Gemini Service...")
    print("=" * 70)

    # Test default model
    service = GeminiService()
    print(f"Default Model: {service.model_name}")
    print(f"Gemini Service available: {service.is_available()}")

    # Test other models
    print("\nSupported Gemini Models:")
    models = ["gemini-1.5-pro", "gemini-2.0-flash-exp", "gemini-exp-1206"]
    for model in models:
        service = GeminiService(model_name=model)
        print(f"  - {model}")

    if not service.is_available():
        print("\nTo enable Gemini service, set environment variable:")
        print("  GEMINI_API_KEY=your_key")

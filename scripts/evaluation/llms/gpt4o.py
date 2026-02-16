#!/usr/bin/env python3
"""
OpenAI GPT-4o service for video analysis.
Uses structured output with Pydantic models and frame extraction.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import os
import logging
from typing import Dict, Optional
from dotenv import load_dotenv

from scripts.evaluation.llms.base import VideoLLMService
from scripts.evaluation.models import CommunityNoteOutput, VideoAnalysisResult
from scripts.evaluation.prompts import PromptTemplate

load_dotenv()
logger = logging.getLogger(__name__)


class GPT4oService(VideoLLMService):
    """OpenAI GPT-4o service for video analysis with structured output."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize GPT-4o service."""
        super().__init__(api_key)
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = "gpt-4o"
        self._client = None

    def is_available(self) -> bool:
        """Check if OpenAI API is available."""
        return bool(self.api_key)

    def _initialize(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.api_key)
                logger.info(f"Initialized OpenAI client: {self.model_name}")
            except ImportError:
                raise ImportError(
                    "openai library not installed. Install with: pip install openai"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize OpenAI: {e}")

    def _extract_frames(self, video_path: str, num_frames: int = 8) -> list:
        """
        Extract frames from video for analysis.

        Args:
            video_path: Path to video file
            num_frames: Number of frames to extract

        Returns:
            List of base64-encoded frames
        """
        try:
            import cv2
            import base64
            import numpy as np

            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Calculate frame indices to extract (evenly spaced)
            frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)

            frames = []
            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    # Encode frame as JPEG
                    _, buffer = cv2.imencode(".jpg", frame)
                    frame_b64 = base64.b64encode(buffer).decode("utf-8")
                    frames.append(frame_b64)

            cap.release()
            logger.info(f"  Extracted {len(frames)} frames from video")
            return frames

        except ImportError:
            logger.error(
                "opencv-python not installed. Install with: pip install opencv-python"
            )
            raise
        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
            raise

    def analyze_video(
        self,
        video_path: str,
        tweet_text: str,
        author_name: str,
        author_username: Optional[str] = None,
        tweet_created_at: Optional[str] = None,
    ) -> Dict:
        """
        Analyze video using GPT-4o with structured output.

        GPT-4o doesn't support direct video input, so we extract frames
        and analyze them as a sequence of images with structured output.

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
                error="OpenAI API key not configured",
                model=self.model_name,
            ).model_dump()

        try:
            self._initialize()

            # Generate prompts using centralized templates
            system_prompt = PromptTemplate.get_system_prompt()
            user_prompt = PromptTemplate.get_structured_prompt(
                tweet_text,
                author_name,
                author_username,
                model_type="gpt4o",
                tweet_created_at=tweet_created_at,
            )

            logger.info(f"Analyzing video with {self.model_name}...")

            # Extract frames from video
            frames = self._extract_frames(video_path, num_frames=8)

            # Create message with frames
            content = [
                {
                    "type": "text",
                    "text": user_prompt
                    + "\n\nAnalyze the following frames from the video in sequence:",
                }
            ]

            # Add each frame
            for i, frame_b64 in enumerate(frames):
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{frame_b64}",
                        },
                    }
                )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ]

            # Generate response with structured output using response_format
            # OpenAI's structured output feature
            response = self._client.beta.chat.completions.parse(
                model=self.model_name,
                messages=messages,
                response_format=CommunityNoteOutput,
                max_tokens=1000,
            )

            # Extract parsed Pydantic object
            community_note = response.choices[0].message.parsed

            if community_note is None:
                # Fallback if parsing failed
                raise ValueError("Failed to parse structured output from GPT-4o")

            result = VideoAnalysisResult(
                success=True,
                model=self.model_name,
                predicted_label=community_note.predicted_label,
                is_misleading=community_note.is_misleading,
                summary=community_note.summary,
                sources=community_note.sources,
                reasons=community_note.reasons,
                confidence=community_note.confidence,
                raw_response=response.choices[0].message.content or "",
            )

            logger.info(
                f"  ✓ Analysis complete (Misleading: {community_note.is_misleading})"
            )
            return result.model_dump()

        except Exception as e:
            logger.error(f"Error analyzing video with GPT-4o: {e}")
            return VideoAnalysisResult(
                success=False,
                error=str(e),
                model=self.model_name,
            ).model_dump()


if __name__ == "__main__":
    # Test GPT-4o service
    print("Testing GPT-4o Service...")
    print("=" * 70)

    service = GPT4oService()
    print(f"GPT-4o Service available: {service.is_available()}")

    if not service.is_available():
        print("\nTo enable GPT-4o service, set environment variable:")
        print("  OPENAI_API_KEY=your_key")

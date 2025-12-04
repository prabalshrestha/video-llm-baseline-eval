#!/usr/bin/env python3
"""
Abstract base class for Video LLM services.
Defines the interface that all video analysis services must implement.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from abc import ABC, abstractmethod
from typing import Dict, Optional

from scripts.evaluation.models import VideoAnalysisResult


class VideoLLMService(ABC):
    """Abstract base class for video LLM services."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the service.

        Args:
            api_key: API key for the service (if None, loads from environment)
        """
        self.api_key = api_key

    @abstractmethod
    def analyze_video(
        self,
        video_path: str,
        tweet_text: str,
        author_name: str,
        author_username: Optional[str] = None,
    ) -> Dict:
        """
        Analyze a video for misinformation.

        Args:
            video_path: Path to the video file
            tweet_text: Text of the tweet
            author_name: Name of the tweet author
            author_username: Username of the tweet author

        Returns:
            Dictionary with analysis results
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the service is available (API key configured)."""
        pass


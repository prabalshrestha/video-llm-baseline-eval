#!/usr/bin/env python3
"""
Qwen VL service for video analysis using Ollama API directly.
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
import requests
from typing import Dict, Optional, TypedDict
from dotenv import load_dotenv

from scripts.evaluation.llms.base import VideoLLMService
from scripts.evaluation.models import CommunityNoteOutput, VideoAnalysisResult
from scripts.evaluation.prompts import PromptTemplate

load_dotenv()
logger = logging.getLogger(__name__)


class QwenService(VideoLLMService):
    """Qwen VL service for video analysis using Ollama API directly.

    Supports TWO types of Ollama models:

    1. LOCAL models (no API key):
       - qwen2.5-vl, qwen3-vl-32b (no -cloud suffix)
       - Run on your machine, 100% free
       - Requires: Ollama installed + model pulled

    2. CLOUD models (API key required):
       - qwen3-vl-cloud, qwen3-vl:235b-cloud (with -cloud suffix)
       - Run on Ollama's servers, no local GPU needed
       - Requires: OLLAMA_API_KEY from https://ollama.com/settings/keys

    Requirements:
    - Ollama installed (https://ollama.ai)
    - For cloud models: OLLAMA_API_KEY environment variable
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "qwen3-vl-cloud",
        ollama_base_url: Optional[str] = None,
    ):
        """Initialize Qwen service with Ollama API.

        Args:
            api_key: Optional OLLAMA_API_KEY for cloud models (can be set via env)
            model_name: Model name (default: qwen3-vl-cloud)
                       - Cloud models (need API key): qwen3-vl-cloud, qwen3-vl:235b-cloud
                       - Local models (no API key): qwen2.5-vl, qwen3-vl-32b
            ollama_base_url: Ollama URL
                            - Local: http://localhost:11434 (default)
                            - Cloud: https://ollama.com (for cloud models)
        """
        super().__init__(api_key)

        # Check for Ollama API key (for cloud models)
        self.ollama_api_key = api_key or os.getenv("OLLAMA_API_KEY")

        self.model_name = model_name
        self.ollama_base_url = ollama_base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.is_cloud_model = "-cloud" in model_name

    def is_available(self) -> bool:
        """Check if Qwen service is available via Ollama."""
        try:
            import requests

            # For cloud models, check if API key is set
            if self.is_cloud_model and not self.ollama_api_key:
                logger.warning(
                    f"Cloud model {self.model_name} requires OLLAMA_API_KEY. "
                    f"Get one at: https://ollama.com/settings/keys or run: ollama signin"
                )
                return False

            # Check if Ollama is running
            headers = {}
            if self.ollama_api_key:
                headers["Authorization"] = f"Bearer {self.ollama_api_key}"

            response = requests.get(
                f"{self.ollama_base_url}/api/tags", headers=headers, timeout=2
            )

            if response.status_code == 200:
                # Check if model is available
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]

                # Try exact match first
                if self.model_name in model_names:
                    return True

                # Try flexible matching for cloud models with version numbers
                # e.g., "qwen3-vl-cloud" should match "qwen3-vl:235b-cloud"
                for name in model_names:
                    # For cloud models, check if the base model and cloud suffix match
                    # Handle cases like: qwen3-vl-cloud -> qwen3-vl:235b-cloud
                    if self.model_name.endswith("-cloud") and name.endswith("-cloud"):
                        # Remove -cloud suffix from both and compare base names
                        requested_base = self.model_name[:-6]  # Remove '-cloud'
                        available_full = name  # e.g., 'qwen3-vl:235b-cloud'

                        # Check if requested base is in the available model name
                        # qwen3-vl should match qwen3-vl:235b-cloud
                        if requested_base in available_full:
                            logger.info(
                                f"Matched requested '{self.model_name}' with available '{name}'"
                            )
                            # Update model_name to exact match
                            self.model_name = name
                            return True
                    # Also try simple substring match for other cases
                    elif (
                        self.model_name in name or name.split(":")[0] in self.model_name
                    ):
                        logger.info(
                            f"Matched requested '{self.model_name}' with available '{name}'"
                        )
                        self.model_name = name
                        return True

                logger.warning(
                    f"Model {self.model_name} not found in Ollama. "
                    f"Available models: {', '.join(model_names)}\n"
                    f"Pull it with: ollama pull {self.model_name}"
                )
                return False
            return False
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            logger.warning("Install Ollama from https://ollama.ai")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Ollama API requests."""
        headers = {"Content-Type": "application/json"}
        if self.is_cloud_model and self.ollama_api_key:
            headers["Authorization"] = f"Bearer {self.ollama_api_key}"
        return headers

    def _call_ollama_api(self, prompt: str, video_path: str) -> Dict:
        """Call Ollama API directly with structured output format.

        Args:
            prompt: The analysis prompt
            video_path: Path to video file

        Returns:
            Dict containing the parsed response
        """
        # Prepare the request
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": f"Video file: {video_path}\n\n{prompt}"}
            ],
            "format": {
                "type": "object",
                "properties": {
                    "predicted_label": {"type": "string"},
                    "is_misleading": {"type": "boolean"},
                    "summary": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "reasons": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string"},
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
            "stream": False,
            "options": {"temperature": 0.0},  # Deterministic for research
        }

        # Make API request
        response = requests.post(
            f"{self.ollama_base_url}/api/chat",
            headers=self._get_headers(),
            json=payload,
            timeout=300,  # 5 minute timeout for video analysis
        )
        response.raise_for_status()

        # Parse response
        result = response.json()
        message_content = result.get("message", {}).get("content", "{}")

        # Parse the JSON response
        try:
            parsed = json.loads(message_content)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama response as JSON: {e}")
            logger.error(f"Raw response: {message_content}")
            raise ValueError(f"Invalid JSON response from Ollama: {e}")

    def analyze_video(
        self,
        video_path: str,
        tweet_text: str,
        author_name: str,
        author_username: Optional[str] = None,
        tweet_created_at: Optional[str] = None,
    ) -> Dict:
        """
        Analyze video using Ollama API with structured output.

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
                error="Qwen service not available. Ollama not running or model not found.",
                model=self.model_name,
            ).model_dump()

        try:
            # Generate prompt
            prompt = PromptTemplate.get_structured_prompt(
                tweet_text,
                author_name,
                author_username,
                model_type="qwen",
                tweet_created_at=tweet_created_at,
            )

            logger.info(f"Analyzing with {self.model_name}...")

            # Call Ollama API
            response_data = self._call_ollama_api(prompt, video_path)

            # Create VideoAnalysisResult from response
            result = VideoAnalysisResult(
                success=True,
                model=self.model_name,
                predicted_label=response_data.get("predicted_label"),
                is_misleading=response_data.get("is_misleading"),
                summary=response_data.get("summary"),
                sources=response_data.get("sources", []),
                reasons=response_data.get("reasons", []),
                confidence=response_data.get("confidence"),
                raw_response=json.dumps(response_data),
            )

            logger.info(f"  ✓ Analysis complete (Misleading: {result.is_misleading})")
            return result.model_dump()

        except Exception as e:
            logger.error(f"Error in Qwen analysis: {e}")
            return VideoAnalysisResult(
                success=False,
                error=str(e),
                model=self.model_name,
            ).model_dump()


if __name__ == "__main__":
    # Test Qwen service with Ollama API
    print("Testing Qwen VL Service (Direct Ollama API Implementation)")
    print("=" * 70)

    # Test Ollama
    print("\nOllama API (Direct HTTP calls):")
    service = QwenService(model_name="qwen3-vl-cloud")
    print(f"  Model: {service.model_name}")
    print(f"  Ollama URL: {service.ollama_base_url}")
    print(f"  Is cloud model: {service.is_cloud_model}")
    print(f"  API key configured: {bool(service.ollama_api_key)}")
    print(f"  Available: {service.is_available()}")

    if not service.is_available():
        print("\n⚠️  Ollama not available!")
        print("\nTo enable Qwen service with Ollama:")
        print("  1. Install Ollama: https://ollama.ai")
        print("  2. Pull the model: ollama pull qwen3-vl-cloud")
        if service.is_cloud_model:
            print("  3. For cloud models, set OLLAMA_API_KEY")
            print("     Get key: https://ollama.com/settings/keys")
        print("  4. Verify: ollama list")

    print("\nSupported Models:")
    print("  LOCAL (no API key):")
    print("    - qwen2.5-vl      - Standard Qwen 2.5 VL model")
    print("    - qwen3-vl-32b    - Larger Qwen 3 model")
    print("  CLOUD (requires OLLAMA_API_KEY):")
    print("    - qwen3-vl-cloud     - Cloud optimized (recommended)")
    print("    - qwen3-vl:235b-cloud - Large cloud model")

    print("\nRequirements:")
    print("  - Ollama installed: https://ollama.ai")
    print("  - requests: pip install requests")
    print("  - Model pulled: ollama pull <model-name>")
    print("  - For cloud models: OLLAMA_API_KEY environment variable")

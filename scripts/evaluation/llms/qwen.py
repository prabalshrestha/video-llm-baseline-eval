#!/usr/bin/env python3
"""
Qwen VL service for video analysis.
Supports Qwen3-VL and Qwen2.5-VL models with native video understanding.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import os
import logging
import json
from typing import Dict, Optional
from dotenv import load_dotenv

from scripts.evaluation.llms.base import VideoLLMService
from scripts.evaluation.models import CommunityNoteOutput, VideoAnalysisResult
from scripts.evaluation.prompts import PromptTemplate

load_dotenv()
logger = logging.getLogger(__name__)


class QwenService(VideoLLMService):
    """Qwen VL service for video analysis.

    Supports multiple Qwen VL models:
    - qwen3-vl-8b-thinking: 8B reasoning-enhanced model
    - qwen3-vl-32b: Mid-tier 32B model
    - qwen2.5-vl-32b-instruct: Best for long-video analysis
    - qwen2.5-vl-7b-instruct: Lightweight 7B model
    - qwen3-vl-235b-a22b: Flagship 235B model (most powerful)

    Note: These are open-source models requiring local deployment or API access.
    """

    # Model name mappings for different deployment methods
    MODEL_NAMES = {
        "qwen3-vl-8b-thinking": "Qwen/Qwen3-VL-8B-Thinking",
        "qwen3-vl-32b": "Qwen/Qwen3-VL-32B",
        "qwen2.5-vl-32b-instruct": "Qwen/Qwen2.5-VL-32B-Instruct",
        "qwen2.5-vl-7b-instruct": "Qwen/Qwen2.5-VL-7B-Instruct",
        "qwen3-vl-235b-a22b": "Qwen/Qwen3-VL-235B-A22B",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "qwen2.5-vl-7b-instruct",
        api_base: Optional[str] = None,
        use_local: bool = False,
    ):
        """Initialize Qwen service.

        Args:
            api_key: API key for Qwen service (e.g., Alibaba Cloud DashScope)
            model_name: Qwen model to use (see MODEL_NAMES)
            api_base: Base URL for API endpoint (if using API)
            use_local: Whether to use local inference (requires model downloaded)
        """
        super().__init__(api_key)
        if not self.api_key:
            self.api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")

        self.model_name = model_name
        self.full_model_name = self.MODEL_NAMES.get(model_name, model_name)
        self.api_base = api_base or os.getenv("QWEN_API_BASE")
        self.use_local = use_local
        self._model = None
        self._processor = None

    def is_available(self) -> bool:
        """Check if Qwen service is available."""
        if self.use_local:
            # For local inference, check if transformers is available
            try:
                import torch
                import transformers

                return True
            except ImportError:
                logger.warning(
                    "Local inference requires: pip install torch transformers qwen-vl-utils"
                )
                return False
        else:
            # For API inference, check if API key is set
            return bool(self.api_key)

    def _initialize_local(self):
        """Initialize local model inference."""
        if self._model is None:
            try:
                from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
                import torch

                logger.info(f"Loading Qwen model locally: {self.full_model_name}")
                logger.info("This may take several minutes for first-time download...")

                # Load model with appropriate dtype
                self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                    self.full_model_name,
                    torch_dtype=(
                        torch.bfloat16 if torch.cuda.is_available() else torch.float32
                    ),
                    device_map="auto",
                )

                self._processor = AutoProcessor.from_pretrained(self.full_model_name)

                logger.info(f"✓ Model loaded successfully: {self.full_model_name}")
            except ImportError as e:
                raise ImportError(
                    f"Required libraries not installed: {e}\n"
                    "Install with: pip install transformers torch qwen-vl-utils"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Qwen model: {e}")

    def _analyze_video_local(self, video_path: str, prompt: str) -> Dict:
        """Analyze video using local model inference."""
        try:
            from qwen_vl_utils import process_vision_info  # type: ignore

            self._initialize_local()

            # Prepare messages with video
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "video",
                            "video": video_path,
                            "max_pixels": 360 * 420,
                            "fps": 1.0,
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            # Prepare inputs
            text = self._processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            image_inputs, video_inputs = process_vision_info(messages)

            inputs = self._processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            )
            inputs = inputs.to(self._model.device)

            # Generate response
            logger.info("Generating response with Qwen model...")
            generated_ids = self._model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=True,
                temperature=0.7,
            )

            generated_ids_trimmed = [
                out_ids[len(in_ids) :]
                for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]

            output_text = self._processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0]

            return output_text

        except Exception as e:
            logger.error(f"Error in local inference: {e}")
            raise

    def _analyze_video_api(self, video_path: str, prompt: str) -> Dict:
        """Analyze video using Qwen API (e.g., DashScope)."""
        try:
            # Try DashScope API first (Alibaba Cloud)
            import dashscope  # type: ignore
            from dashscope import MultiModalConversation  # type: ignore

            dashscope.api_key = self.api_key

            # Upload video file
            logger.info(f"Uploading video to DashScope: {video_path}")
            local_file = f"file://{os.path.abspath(video_path)}"

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"video": local_file},
                        {"text": prompt},
                    ],
                }
            ]

            # Call API
            logger.info(f"Calling DashScope API with model: {self.full_model_name}")
            response = MultiModalConversation.call(
                model=self.full_model_name,
                messages=messages,
            )

            if response.status_code == 200:
                output_text = response.output.choices[0].message.content[0]["text"]
                return output_text
            else:
                raise RuntimeError(f"API call failed: {response.message}")

        except ImportError:
            raise ImportError(
                "DashScope not installed. Install with: pip install dashscope"
            )
        except Exception as e:
            logger.error(f"Error in API inference: {e}")
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
        Analyze video using Qwen VL model.

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
                error="Qwen service not available (check API key or local setup)",
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

            # Add explicit JSON instruction for Qwen
            prompt += "\n\nIMPORTANT: Respond ONLY with a valid JSON object containing the required fields. Do not include any other text."

            logger.info(f"Analyzing video with {self.model_name}...")

            # Choose inference method
            if self.use_local:
                output_text = self._analyze_video_local(video_path, prompt)
            else:
                output_text = self._analyze_video_api(video_path, prompt)

            # Parse JSON response
            # Try to extract JSON from response (in case model adds extra text)
            import re

            json_match = re.search(r"\{.*\}", output_text, re.DOTALL)
            if json_match:
                output_text = json_match.group(0)

            response_data = json.loads(output_text)

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
                raw_response=output_text,
            )

            logger.info(
                f"  ✓ Analysis complete (Misleading: {community_note.is_misleading})"
            )
            return result.model_dump()

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Qwen response: {e}")
            logger.error(f"Raw response: {output_text[:500]}...")
            return VideoAnalysisResult(
                success=False,
                error=f"Invalid JSON response from model: {str(e)}",
                model=self.model_name,
                raw_response=output_text,
            ).model_dump()

        except Exception as e:
            logger.error(f"Error analyzing video with Qwen: {e}")
            return VideoAnalysisResult(
                success=False,
                error=str(e),
                model=self.model_name,
            ).model_dump()


if __name__ == "__main__":
    # Test Qwen service
    print("Testing Qwen VL Service...")
    print("=" * 70)

    # Test API mode
    print("\nAPI Mode:")
    service_api = QwenService(model_name="qwen2.5-vl-7b-instruct", use_local=False)
    print(f"  Model: {service_api.model_name}")
    print(f"  Full name: {service_api.full_model_name}")
    print(f"  Available: {service_api.is_available()}")

    # Test local mode
    print("\nLocal Mode:")
    service_local = QwenService(model_name="qwen2.5-vl-7b-instruct", use_local=True)
    print(f"  Model: {service_local.model_name}")
    print(f"  Available: {service_local.is_available()}")

    print("\nSupported Qwen Models:")
    for model_key in QwenService.MODEL_NAMES.keys():
        print(f"  - {model_key}")

    if not service_api.is_available() and not service_local.is_available():
        print("\nTo enable Qwen service:")
        print("  API Mode: Set QWEN_API_KEY or DASHSCOPE_API_KEY environment variable")
        print("  Local Mode: Install required packages:")
        print("    pip install torch transformers qwen-vl-utils dashscope")

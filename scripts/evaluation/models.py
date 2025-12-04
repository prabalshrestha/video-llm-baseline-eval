#!/usr/bin/env python3
"""
Pydantic models for structured LLM outputs.
Ensures consistent response format from different LLMs.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CommunityNoteOutput(BaseModel):
    """Structured output for Community Note-style fact-checking."""

    is_misleading: bool = Field(
        description="Whether the video content is misleading or contains misinformation"
    )

    summary: str = Field(
        description="Concise explanation (2-3 sentences) of why the content is misleading, or 'No issues detected' if not misleading"
    )

    reasons: List[str] = Field(
        default_factory=list,
        description="List of applicable misinformation categories: 'factual_error', 'manipulated_media', 'missing_context', 'outdated_info', 'unverified_claim'"
    )

    confidence: str = Field(
        description="Confidence level in the assessment: 'high', 'medium', or 'low'"
    )

    explanation: Optional[str] = Field(
        default=None,
        description="Additional context or reasoning for the assessment"
    )


class VideoAnalysisResult(BaseModel):
    """Complete result of video analysis including metadata."""

    success: bool = Field(description="Whether the analysis completed successfully")
    
    model: str = Field(description="Name of the model used for analysis")
    
    is_misleading: bool = Field(
        default=False,
        description="Whether content is misleading"
    )
    
    summary: str = Field(
        default="",
        description="Community note summary"
    )
    
    reasons: List[str] = Field(
        default_factory=list,
        description="List of misinformation categories"
    )
    
    confidence: str = Field(
        default="medium",
        description="Confidence level"
    )
    
    raw_response: Optional[str] = Field(
        default=None,
        description="Raw LLM response"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Error message if analysis failed"
    )


# Valid reason categories
VALID_REASONS = [
    "factual_error",
    "manipulated_media",
    "missing_context",
    "outdated_info",
    "unverified_claim",
]

# Valid confidence levels
VALID_CONFIDENCE = ["high", "medium", "low"]


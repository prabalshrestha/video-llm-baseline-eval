#!/usr/bin/env python3
"""
Pydantic models for structured LLM outputs.
Ensures consistent response format from different LLMs.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


# Type alias for valid reason categories (based on Community Notes definitions)
ReasonCategory = Literal[
    "factual_error",  # The post contains factual inaccuracies
    "manipulated_media",  # The post includes manipulated, fake, or out-of-context media
    "outdated_information",  # The post shares information that is no longer current or accurate
    "missing_important_context",  # The post omits critical context that changes the meaning
    "disputed_claim_as_fact",  # The post presents unverified or disputed claims as facts
    "misinterpreted_satire",  # The post is satire likely to be mistaken for a factual claim
    "other",  # The post is misleading for misleading_tags not covered above
]


# Type alias for confidence levels
ConfidenceLevel = Literal["high", "medium", "low"]


class CommunityNoteOutput(BaseModel):
    """Structured output for Community Note-style fact-checking."""

    predicted_label: str = Field(
        description="One-phrase assessment label (e.g., 'Misleading', 'Accurate', 'Partially Accurate', 'Potentially Misinterpreted', 'Out of Context', 'Unverified')"
    )

    is_misleading: bool = Field(
        description="Whether the video content is misleading or contains misinformation"
    )

    summary: str = Field(
        description="Concise explanation (2-3 sentences) with source URLs of why the content is misleading, or 'No issues detected' if not misleading"
    )

    sources: List[str] = Field(
        default_factory=list,
        description="List of URLs or references used to verify claims",
    )

    misleading_tags: List[str] = Field(
        default_factory=list,
        description="List of applicable misinformation categories: 'factual_error', 'manipulated_media', 'outdated_information', 'missing_important_context', 'disputed_claim_as_fact', 'misinterpreted_satire', 'other'",
    )

    confidence: ConfidenceLevel = Field(
        description="Confidence level in the assessment: 'high', 'medium', or 'low'"
    )

    explanation: Optional[str] = Field(
        default=None, description="Additional context or reasoning for the assessment"
    )


class VideoAnalysisResult(BaseModel):
    """Complete result of video analysis including metadata."""

    success: bool = Field(description="Whether the analysis completed successfully")

    model: str = Field(description="Name of the model used for analysis")

    predicted_label: str = Field(default="", description="One-phrase assessment label")

    is_misleading: bool = Field(
        default=False, description="Whether content is misleading"
    )

    summary: str = Field(default="", description="Community note summary")

    sources: List[str] = Field(
        default_factory=list,
        description="List of URLs or references used to verify claims",
    )

    # misleading_tags: List[ReasonCategory] = Field(
    #     default_factory=list, description="List of misinformation categories"
    # )

    misleading_tags: List[str] = Field(
        default_factory=list,
        description="List of misinformation categories (e.g., 'factual_error', 'manipulated_media', 'outdated_information', 'missing_important_context', 'disputed_claim_as_fact', 'misinterpreted_satire', 'other')",
    )

    confidence: ConfidenceLevel = Field(
        default="medium", description="Confidence level"
    )

    raw_response: Optional[str] = Field(default=None, description="Raw LLM response")

    error: Optional[str] = Field(
        default=None, description="Error message if analysis failed"
    )

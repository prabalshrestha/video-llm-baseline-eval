#!/usr/bin/env python3
"""
Prompt templates for Video LLM evaluation.
Centralized prompt generation for consistent misinformation detection across all models.
"""

from typing import Optional


class PromptTemplate:
    """Manages prompts for video misinformation detection."""

    @staticmethod
    def get_system_prompt() -> str:
        """
        Get the system prompt for models that support it (like GPT-4o).

        Returns:
            System prompt string defining the AI's role and expertise
        """
        return """You are an expert fact-checker specializing in video content analysis and misinformation detection. You have deep knowledge of common manipulation techniques, deepfakes, and misleading editing practices. You provide clear, evidence-based explanations similar to X/Twitter's Community Notes system."""

    @staticmethod
    def get_structured_prompt(
        tweet_text: str,
        author_name: str,
        author_username: Optional[str] = None,
        model_type: str = "gemini",
    ) -> str:
        """
        Generate a structured prompt for video misinformation analysis.

        This prompt is designed for models with structured output (JSON schema enforcement).

        Args:
            tweet_text: The text content of the tweet
            author_name: Name of the tweet author
            author_username: Username of the tweet author (optional)
            model_type: Type of model ("gemini" for video, "gpt4o" for frames)

        Returns:
            Formatted prompt string optimized for structured JSON output
        """
        author_info = (
            f"{author_name} (@{author_username})" if author_username else author_name
        )

        # Model-specific video instruction
        if model_type == "gpt4o":
            video_instruction = "Analyze the video frames carefully to determine whether the content is misleading or contains misinformation."
        elif model_type == "qwen":
            video_instruction = "Watch the video carefully, analyzing both visual and audio content to determine whether the content is misleading or contains misinformation."
        else:
            video_instruction = "Watch the video carefully and analyze whether the content is misleading or contains misinformation."

        prompt = f"""You are an expert fact-checker analyzing video content for potential misinformation, similar to X/Twitter's Community Notes system.

**Context:**
Tweet Author: {author_info}
Tweet Text: "{tweet_text}"

**Your Task:**
{video_instruction}

**Instructions:**
1. Determine if this content is misleading (true/false)
2. Provide a concise Community Note (2-3 sentences) explaining why the content is misleading, or write "No issues detected" if not misleading
3. Identify applicable misinformation categories from: factual_error, manipulated_media, missing_context, outdated_info, unverified_claim
4. Indicate your confidence level: high, medium, or low

**Response Format:**
Return a JSON object with these exact fields:
- is_misleading (boolean): true if misleading, false otherwise
- summary (string): Clear, factual explanation in 2-3 sentences
- reasons (array of strings): List applicable categories, or empty array if not misleading
- confidence (string): "high", "medium", or "low"
- explanation (string): Additional context if needed

**Guidelines:**
- Be objective and factual
- Focus on verifiable information
- Consider context carefully
- Cite specific details from the video{' or visible in the frames' if model_type == 'gpt4o' else ''}
- If uncertain, indicate lower confidence"""

        return prompt


# Convenience functions for backward compatibility
def get_system_prompt() -> str:
    """Get the system prompt."""
    return PromptTemplate.get_system_prompt()


def get_structured_prompt(
    tweet_text: str,
    author_name: str,
    author_username: Optional[str] = None,
    model_type: str = "gemini",
) -> str:
    """Get the structured prompt."""
    return PromptTemplate.get_structured_prompt(
        tweet_text, author_name, author_username, model_type
    )


if __name__ == "__main__":
    # Test the prompt templates
    print("=" * 70)
    print("SYSTEM PROMPT")
    print("=" * 70)
    print(PromptTemplate.get_system_prompt())

    print("\n" + "=" * 70)
    print("GEMINI STRUCTURED PROMPT (Example)")
    print("=" * 70)
    sample_prompt = PromptTemplate.get_structured_prompt(
        tweet_text="🚨| BREAKING: Speed just met the PRESIDENT OF CHILE 😭😭😭",
        author_name="Speedy HQ",
        author_username="IShowSpeedHQ",
        model_type="gemini",
    )
    print(sample_prompt)

    print("\n" + "=" * 70)
    print("GPT-4O STRUCTURED PROMPT (Example)")
    print("=" * 70)
    sample_prompt_gpt = PromptTemplate.get_structured_prompt(
        tweet_text="🚨| BREAKING: Speed just met the PRESIDENT OF CHILE 😭😭😭",
        author_name="Speedy HQ",
        author_username="IShowSpeedHQ",
        model_type="gpt4o",
    )
    print(sample_prompt_gpt)

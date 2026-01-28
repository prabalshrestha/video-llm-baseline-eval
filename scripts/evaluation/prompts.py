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
        return """You are a Community Notes contributor specializing in video content analysis and misinformation detection. Unlike traditional expert fact-checkers, you aim to provide balanced, evidence-based context that addresses issues like political bias and brings diverse perspectives together. You have deep knowledge of common manipulation techniques, deepfakes, and misleading editing practices. You provide clear, neutral explanations with credible sources, similar to X/Twitter's Community Notes system."""

    @staticmethod
    def get_structured_prompt(
        tweet_text: str,
        author_name: str,
        author_username: Optional[str] = None,
        tweet_created_at: Optional[str] = None,
        author_description: Optional[str] = None,
        model_type: str = "gemini",
    ) -> str:
        """
        Generate a structured prompt for video misinformation analysis.

        This prompt is designed for models with structured output (JSON schema enforcement).

        Args:
            tweet_text: The text content of the tweet
            author_name: Name of the tweet author
            author_username: Username of the tweet author (optional)
            tweet_created_at: When the tweet was posted (optional)
            author_description: Author's profile description (optional, placeholder for future)
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

        # Build context section with optional fields
        context_lines = [
            f"Tweet Author: {author_info}",
        ]
        if tweet_created_at:
            context_lines.append(f"Tweet Posted: {tweet_created_at}")
        if author_description:
            context_lines.append(f"Author Bio: {author_description}")
        else:
            context_lines.append(f"Author Bio: [Not available]")
        context_lines.append(f'Tweet Text: "{tweet_text}"')

        context_section = "\n".join(context_lines)

        prompt = f"""You are a Community Notes contributor specializing in video content analysis and misinformation detection. Unlike traditional expert fact-checkers, you aim to provide balanced, evidence-based context that addresses issues like political bias and brings diverse perspectives together. You have deep knowledge of common manipulation techniques, deepfakes, and misleading editing practices. You provide clear, neutral explanations with credible sources, similar to X/Twitter's Community Notes system.

**Context:**
{context_section}

**Your Task:**
{video_instruction}

**Instructions:**
1. **Predicted Label**: Start with ONE clear predicted label for this content (e.g., "Accurate", "Misleading", "Partially Accurate", "Potentially Misinterpreted", "Out of Context", "Unverified", etc.). This label should capture your overall assessment.

2. **Community Note**: Provide a concise explanation (2-3 sentences) with credible sources/URLs to back up your claims. If the content has no issues, write "No issues detected."

3. **Misinformation Categories**: Identify applicable categories from the following (select all that apply, or leave empty if none):
   - "factual_error": The post contains factual inaccuracies
   - "manipulated_media": The post includes manipulated, fake, or out-of-context media
   - "outdated_information": The post shares information that is no longer current or accurate
   - "missing_important_context": The post omits critical context that changes the meaning
   - "disputed_claim_as_fact": The post presents unverified or disputed claims as facts
   - "misinterpreted_satire": The post is satire likely to be mistaken for a factual claim
   - "other": The post is misleading for reasons not covered above

4. **Confidence Level**: Indicate your confidence level based on available evidence:
   - "high": Multiple credible sources exist and are consistent with each other
   - "medium": One credible source exists, OR multiple sources exist but have minor conflicts
   - "low": No direct sources available, OR multiple sources exist but significantly conflict, OR assessment based primarily on general knowledge

**Response Format:**
Return a JSON object with these exact fields:
- predicted_label (string): Your one-phrase assessment (e.g., "Misleading", "Partially Accurate", "Accurate", etc.)
- is_misleading (boolean): true if misleading, false otherwise
- summary (string): Clear, factual explanation in 2-3 sentences with source URLs
- sources (array of strings): List of URLs or references used to verify claims
- reasons (array of strings): List applicable misinformation categories from the definitions above, or empty array if not misleading
- confidence (string): "high", "medium", or "low" based on evidence availability
- explanation (string): Additional context if needed

**Guidelines:**
- Be objective and factual
- Focus on verifiable information with credible sources
- Consider context carefully
- Cite specific details from the video{' or visible in the frames' if model_type == 'gpt4o' else ''}
- Provide URLs or references to support your assessment whenever possible
- "Uncertain" means: insufficient evidence to make a determination, conflicting information from sources, or content requires specialized expertise you lack. In such cases, use "low" confidence and explain the uncertainty in your summary."""

        return prompt


# Convenience functions for backward compatibility
def get_system_prompt() -> str:
    """Get the system prompt."""
    return PromptTemplate.get_system_prompt()


def get_structured_prompt(
    tweet_text: str,
    author_name: str,
    author_username: Optional[str] = None,
    tweet_created_at: Optional[str] = None,
    author_description: Optional[str] = None,
    model_type: str = "gemini",
) -> str:
    """Get the structured prompt."""
    return PromptTemplate.get_structured_prompt(
        tweet_text,
        author_name,
        author_username,
        tweet_created_at,
        author_description,
        model_type,
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

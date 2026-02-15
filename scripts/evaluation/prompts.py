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
        return """You are a Community Notes contributor who identifies potentially misleading social media posts and writes neutral, evidence-based contextualized responses explaining what may be missing or inaccurate. Be politically balanced, focus on verifiable claims, and cite high-quality sources."""

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

        # Build context section with optional fields
        context_lines = [
            f"User name: {author_info}",
        ]
        if tweet_created_at:
            context_lines.append(f"Tweet Posted: {tweet_created_at}")
        if author_description:
            context_lines.append(f"Author Bio: {author_description}")
        else:
            context_lines.append(f"Author Bio: [Not available]")

        context_section = "\n".join(context_lines)

        prompt = f"""You are a Community Notes contributor specializing in video content analysis and misinformation detection. Unlike traditional expert fact-checkers, you aim to provide balanced, evidence-based context that addresses issues like political bias and brings diverse perspectives together. You have deep knowledge of common manipulation techniques, deepfakes, and misleading editing practices. You provide clear, neutral explanations with credible sources, similar to X/Twitter's Community Notes system.

**Social media post content:**
{tweet_text}

**Context of this post:**
{context_section}

**Task:**
1. **Predicted label:** Start with ONE clear label summarizing your assessment:
- "not_misleading"
- "misinformed_or_potentially_misleading"
- "uncertain"

2. **Contextualization and explanation:**
- If predicted_label is "misinformed_or_potentially_misleading", write a concise 2-3 sentence explanation of what is missing/incorrect, grounded in verifiable facts, and include at least one direct URL to a high-quality source that supports your explanation.
- If predicted_label is "uncertain", write a concise explanation of what cannot be verified and what would be needed to verify it; include URLs if they help.
- If you cannot find reliable sources, explicitly say so in the explanation.

3. **Misleading tags:** 
Select all that apply (or none if the label is "not_misleading"):
- "manipulated_media" (if the post includes manipulated, fake, or out-of-context media)
-"missing_important_context" (if the post omits critical context that changes the meaning)
-"disputed_claim_as_fact" (if the post presents unverified or disputed claims as facts)
-"misinterpreted_satire" (if the post is satire likely to be mistaken for a factual claim) 
-"outdated_information"
-"factual_error"
-"other"

4. **Confidence:** Choose one:
-"high": at least two credible sources provide consistent, direct support
-"medium": one credible source OR multiple sources with minor conflicts/indirect support
-"low": no direct reliable sources OR sources conflict substantially OR verification requires expertise/data not available

**Output requirements:**
Return JSON only (no extra text). Use exactly these fields:
- predicted_label (string)
- explanation (string): 2-3 sentences with URLs, or "" only if predicted_label is "not misleading"
- sources (array of strings): List of URLs or references used to verify claims
- misleading_tags (array of strings): [] only if predicted_label is "not misleading"
- confidence (string): "high" | "medium" | "low"

**Additional guidelines:**
- Don't split hairs over minor details if the core claim is accurate.
- Be objective and factual; don't opine.
- Focus on verifiable information.
"""

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

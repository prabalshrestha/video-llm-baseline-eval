#!/usr/bin/env python3
"""
Evaluation metrics for comparing LLM outputs with human community notes.
Includes text similarity (ROUGE, BLEU) and semantic similarity measures.
"""

import logging
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)


class EvaluationMetrics:
    """Calculate various metrics for comparing LLM outputs with human notes."""

    def __init__(self):
        """Initialize the metrics calculator."""
        self._rouge_scorer = None
        self._sentence_model = None
        self._nltk_initialized = False

    def _initialize_rouge(self):
        """Lazy initialization of ROUGE scorer."""
        if self._rouge_scorer is None:
            try:
                from rouge_score import rouge_scorer

                self._rouge_scorer = rouge_scorer.RougeScorer(
                    ["rouge1", "rouge2", "rougeL"], use_stemmer=True
                )
                logger.info("Initialized ROUGE scorer")
            except ImportError:
                logger.error(
                    "rouge-score library not installed. Install with: pip install rouge-score"
                )
                raise

    def _initialize_sentence_transformer(self):
        """Lazy initialization of sentence transformer model."""
        if self._sentence_model is None:
            try:
                from sentence_transformers import SentenceTransformer

                # Use a lightweight but effective model
                self._sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Initialized sentence transformer model")
            except ImportError:
                logger.error(
                    "sentence-transformers library not installed. "
                    "Install with: pip install sentence-transformers"
                )
                raise

    def _initialize_nltk(self):
        """Initialize NLTK for BLEU scoring."""
        if not self._nltk_initialized:
            try:
                import nltk

                # Try to download required data if not present
                try:
                    nltk.data.find("tokenizers/punkt")
                except LookupError:
                    nltk.download("punkt", quiet=True)

                self._nltk_initialized = True
                logger.info("Initialized NLTK")
            except ImportError:
                logger.error("nltk library not installed. Install with: pip install nltk")
                raise

    def calculate_rouge_scores(
        self, hypothesis: str, reference: str
    ) -> Dict[str, float]:
        """
        Calculate ROUGE scores (ROUGE-1, ROUGE-2, ROUGE-L).

        ROUGE measures n-gram overlap between hypothesis and reference.
        Higher scores indicate more similar texts.

        Args:
            hypothesis: Generated text (LLM output)
            reference: Reference text (human community note)

        Returns:
            Dictionary with rouge1, rouge2, and rougeL F1 scores
        """
        if not hypothesis or not reference:
            return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}

        try:
            self._initialize_rouge()
            scores = self._rouge_scorer.score(reference, hypothesis)

            return {
                "rouge1": scores["rouge1"].fmeasure,
                "rouge2": scores["rouge2"].fmeasure,
                "rougeL": scores["rougeL"].fmeasure,
            }
        except Exception as e:
            logger.error(f"Error calculating ROUGE scores: {e}")
            return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}

    def calculate_bleu_score(
        self, hypothesis: str, reference: str
    ) -> float:
        """
        Calculate BLEU score.

        BLEU measures precision-focused similarity, commonly used in translation.

        Args:
            hypothesis: Generated text (LLM output)
            reference: Reference text (human community note)

        Returns:
            BLEU score (0-1, higher is better)
        """
        if not hypothesis or not reference:
            return 0.0

        try:
            self._initialize_nltk()
            from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

            # Tokenize
            reference_tokens = [reference.lower().split()]
            hypothesis_tokens = hypothesis.lower().split()

            # Use smoothing to avoid zero scores for short texts
            smoothing = SmoothingFunction().method1

            score = sentence_bleu(
                reference_tokens, hypothesis_tokens, smoothing_function=smoothing
            )
            return score

        except Exception as e:
            logger.error(f"Error calculating BLEU score: {e}")
            return 0.0

    def calculate_semantic_similarity(
        self, text1: str, text2: str
    ) -> float:
        """
        Calculate semantic similarity using sentence embeddings.

        Uses cosine similarity between sentence embeddings to measure
        semantic closeness regardless of exact wording.

        Args:
            text1: First text (LLM output)
            text2: Second text (human community note)

        Returns:
            Cosine similarity score (0-1, higher indicates more similar meaning)
        """
        if not text1 or not text2:
            return 0.0

        try:
            # Lazy import to avoid segfault on module load
            import numpy as np
            
            self._initialize_sentence_transformer()

            # Generate embeddings
            embeddings = self._sentence_model.encode([text1, text2])

            # Calculate cosine similarity
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )

            # Convert to float and ensure in range [0, 1]
            return float(max(0.0, min(1.0, similarity)))

        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.0

    def calculate_classification_accuracy(
        self, predicted: bool, actual: bool
    ) -> bool:
        """
        Calculate binary classification accuracy (is_misleading).

        Args:
            predicted: LLM's prediction (is_misleading)
            actual: Ground truth from human note

        Returns:
            True if prediction matches actual, False otherwise
        """
        return predicted == actual

    def calculate_reason_overlap(
        self, predicted_reasons: List[str], actual_reasons: List[str]
    ) -> Dict[str, float]:
        """
        Calculate overlap between predicted and actual reason categories.

        Args:
            predicted_reasons: List of reasons identified by LLM
            actual_reasons: List of actual reasons from human note

        Returns:
            Dictionary with precision, recall, and F1 scores
        """
        if not actual_reasons:
            # If no actual reasons, perfect score if no predictions
            if not predicted_reasons:
                return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
            else:
                return {"precision": 0.0, "recall": 1.0, "f1": 0.0}

        if not predicted_reasons:
            return {"precision": 1.0, "recall": 0.0, "f1": 0.0}

        # Convert to sets for easier comparison
        pred_set = set(predicted_reasons)
        actual_set = set(actual_reasons)

        # Calculate intersection
        intersection = pred_set & actual_set

        # Calculate precision, recall, F1
        precision = len(intersection) / len(pred_set) if pred_set else 0.0
        recall = len(intersection) / len(actual_set) if actual_set else 0.0

        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    def compare_outputs(
        self,
        llm_output: Dict,
        human_note: Dict,
    ) -> Dict[str, any]:
        """
        Compare LLM output with human community note across all metrics.

        Args:
            llm_output: Dictionary with LLM analysis results
                - is_misleading: bool
                - summary: str
                - misleading_tags: List[str]
            human_note: Dictionary with human community note
                - is_misleading: bool
                - summary: str
                - misleading_tags: dict or list

        Returns:
            Dictionary with all computed metrics
        """
        metrics = {}

        # Text similarity metrics
        llm_summary = llm_output.get("summary", "")
        human_summary = human_note.get("summary", "")

        rouge_scores = self.calculate_rouge_scores(llm_summary, human_summary)
        metrics.update(rouge_scores)

        metrics["bleu"] = self.calculate_bleu_score(llm_summary, human_summary)
        metrics["semantic_similarity"] = self.calculate_semantic_similarity(
            llm_summary, human_summary
        )

        # Classification accuracy
        llm_is_misleading = llm_output.get("is_misleading", False)
        human_is_misleading = human_note.get("is_misleading", True)
        metrics["classification_correct"] = self.calculate_classification_accuracy(
            llm_is_misleading, human_is_misleading
        )

        # Reason overlap
        llm_reasons = llm_output.get("misleading_tags", llm_output.get("reasons", []))
        human_reasons = self._extract_human_misleading_tags(human_note)
        reason_metrics = self.calculate_reason_overlap(llm_reasons, human_reasons)
        metrics["reason_precision"] = reason_metrics["precision"]
        metrics["reason_recall"] = reason_metrics["recall"]
        metrics["reason_f1"] = reason_metrics["f1"]

        return metrics

    def _extract_human_misleading_tags(self, human_note: Dict) -> List[str]:
        """
        Extract misleading tag categories from human note.

        Handles both dict format (with 0/1 values) and list format.
        Supports legacy "reasons" key for backward compatibility.

        Args:
            human_note: Human community note data

        Returns:
            List of misleading tag category names
        """
        reasons_data = human_note.get("misleading_tags", human_note.get("reasons", {}))

        if isinstance(reasons_data, dict):
            # Dict format: {"factual_error": 1, "missing_context": 1, ...}
            return [key for key, value in reasons_data.items() if value == 1]
        elif isinstance(reasons_data, list):
            # List format: ["factual_error", "missing_context", ...]
            return reasons_data
        else:
            return []

    def calculate_aggregate_metrics(
        self, all_results: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate aggregate metrics across all samples.

        Args:
            all_results: List of result dictionaries with metrics

        Returns:
            Dictionary with averaged metrics
        """
        if not all_results:
            return {}

        # Initialize accumulators
        metric_sums = {}
        metric_counts = {}

        # Sum up all metrics
        for result in all_results:
            metrics = result.get("metrics", {})
            for key, value in metrics.items():
                if isinstance(value, (int, float, bool)):
                    if key not in metric_sums:
                        metric_sums[key] = 0
                        metric_counts[key] = 0
                    metric_sums[key] += float(value)
                    metric_counts[key] += 1

        # Calculate averages
        aggregate = {}
        for key in metric_sums:
            aggregate[f"avg_{key}"] = metric_sums[key] / metric_counts[key]

        return aggregate


if __name__ == "__main__":
    # Test the metrics
    print("Testing Evaluation Metrics...")
    print("=" * 70)

    metrics = EvaluationMetrics()

    # Sample texts
    reference = "The president of Chile is Gabriel Boric Font. The person in the video is Marc Etienne Celestin."
    hypothesis = "This video incorrectly identifies someone as the president of Chile. The actual president is Gabriel Boric."

    print("\nReference:", reference)
    print("Hypothesis:", hypothesis)
    print("\n" + "=" * 70)

    # ROUGE scores
    rouge = metrics.calculate_rouge_scores(hypothesis, reference)
    print(f"\nROUGE-1: {rouge['rouge1']:.3f}")
    print(f"ROUGE-2: {rouge['rouge2']:.3f}")
    print(f"ROUGE-L: {rouge['rougeL']:.3f}")

    # BLEU score
    bleu = metrics.calculate_bleu_score(hypothesis, reference)
    print(f"\nBLEU: {bleu:.3f}")

    # Semantic similarity
    semantic = metrics.calculate_semantic_similarity(hypothesis, reference)
    print(f"\nSemantic Similarity: {semantic:.3f}")

    print("\n" + "=" * 70)
    print("✓ Metrics test complete")


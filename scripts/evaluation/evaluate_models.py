#!/usr/bin/env python3
"""
Main evaluation script for Video LLM baseline.
Runs evaluation on videos using Gemini 1.5 Pro and GPT-4o.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional
from tqdm import tqdm

from scripts.evaluation.llms import GeminiService, GPT4oService
from scripts.evaluation.metrics import EvaluationMetrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VideoLLMEvaluator:
    """Main evaluator for testing Video LLMs on misinformation detection."""

    def __init__(
        self,
        dataset_path: str = "data/evaluation/dataset.json",
        output_dir: str = "data/evaluation",
        cache_file: Optional[str] = None,
    ):
        """
        Initialize the evaluator.

        Args:
            dataset_path: Path to the evaluation dataset JSON
            output_dir: Directory to save results
            cache_file: Optional path to cache file for resuming evaluations
        """
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize services
        self.gemini = GeminiService()
        self.gpt4o = GPT4oService()
        self.metrics = EvaluationMetrics()

        # Load dataset
        self.dataset = self._load_dataset()

        # Cache management
        self.cache_file = Path(cache_file) if cache_file else None
        self.cache = self._load_cache()

        logger.info(f"Initialized evaluator with {len(self.dataset)} samples")

    def _load_dataset(self) -> Dict:
        """Load the evaluation dataset."""
        try:
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Loaded dataset: {self.dataset_path}")
            return data
        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            raise

    def _load_cache(self) -> Dict:
        """Load cached results if available."""
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                logger.info(f"Loaded cache with {len(cache)} entries")
                return cache
            except Exception as e:
                logger.warning(f"Error loading cache: {e}")
        return {}

    def _save_cache(self):
        """Save cache to disk."""
        if self.cache_file:
            try:
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self.cache, f, indent=2)
            except Exception as e:
                logger.warning(f"Error saving cache: {e}")

    def evaluate_sample(
        self,
        sample: Dict,
        models: List[str] = ["gemini", "gpt4o"],
        use_cache: bool = True,
    ) -> Dict:
        """
        Evaluate a single video sample with specified models.

        Args:
            sample: Sample data from dataset
            models: List of models to use ('gemini', 'gpt4o')
            use_cache: Whether to use cached results

        Returns:
            Dictionary with evaluation results
        """
        sample_id = sample["metadata"]["sample_id"]
        video_path = sample["video"]["path"]
        tweet_text = sample["tweet"]["text"]
        author_name = sample["tweet"]["author_name"]
        author_username = sample["tweet"].get("author_username")
        human_note = sample["community_note"]

        result = {
            "sample_id": sample_id,
            "video_path": video_path,
            "tweet_text": tweet_text,
            "human_note": {
                "is_misleading": human_note["is_misleading"],
                "summary": human_note["summary"],
                "reasons": human_note["reasons"],
            },
        }

        # Check cache
        if use_cache and sample_id in self.cache:
            cached = self.cache[sample_id]
            logger.info(f"Using cached results for {sample_id}")
            return cached

        # Evaluate with Gemini
        if "gemini" in models and self.gemini.is_available():
            logger.info(f"Evaluating {sample_id} with Gemini...")
            gemini_output = self.gemini.analyze_video(
                video_path, tweet_text, author_name, author_username
            )
            result["gemini_output"] = gemini_output

            # Calculate metrics
            if gemini_output.get("success"):
                gemini_metrics = self.metrics.compare_outputs(gemini_output, human_note)
                result["gemini_metrics"] = gemini_metrics

        elif "gemini" in models:
            logger.warning("Gemini API not available - skipping")

        # Evaluate with GPT-4o
        if "gpt4o" in models and self.gpt4o.is_available():
            logger.info(f"Evaluating {sample_id} with GPT-4o...")
            gpt4o_output = self.gpt4o.analyze_video(
                video_path, tweet_text, author_name, author_username
            )
            result["gpt4o_output"] = gpt4o_output

            # Calculate metrics
            if gpt4o_output.get("success"):
                gpt4o_metrics = self.metrics.compare_outputs(gpt4o_output, human_note)
                result["gpt4o_metrics"] = gpt4o_metrics

        elif "gpt4o" in models:
            logger.warning("GPT-4o API not available - skipping")

        # Cache result
        self.cache[sample_id] = result
        self._save_cache()

        return result

    def evaluate_all(
        self,
        models: List[str] = ["gemini", "gpt4o"],
        limit: Optional[int] = None,
        use_cache: bool = True,
    ) -> List[Dict]:
        """
        Evaluate all samples in the dataset.

        Args:
            models: List of models to use
            limit: Maximum number of samples to evaluate
            use_cache: Whether to use cached results

        Returns:
            List of evaluation results
        """
        samples = self.dataset.get("samples", [])
        if limit:
            samples = samples[:limit]

        logger.info(f"Evaluating {len(samples)} samples with models: {models}")

        results = []
        for sample in tqdm(samples, desc="Evaluating videos"):
            try:
                result = self.evaluate_sample(sample, models, use_cache)
                results.append(result)
            except Exception as e:
                logger.error(f"Error evaluating {sample['metadata']['sample_id']}: {e}")
                # Continue with next sample

        return results

    def save_results(self, results: List[Dict], output_path: Optional[str] = None):
        """
        Save evaluation results to JSON file.

        Args:
            results: List of evaluation results
            output_path: Optional custom output path
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"llm_results_{timestamp}.json"
        else:
            output_path = Path(output_path)

        # Prepare output
        output_data = {
            "evaluation_info": {
                "timestamp": datetime.now().isoformat(),
                "dataset": str(self.dataset_path),
                "total_samples": len(results),
            },
            "results": results,
        }

        # Add aggregate statistics
        output_data["aggregate_metrics"] = self._calculate_aggregate_stats(results)

        # Save to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to: {output_path}")
        return output_path

    def generate_summary_report(
        self, results: List[Dict], output_path: Optional[str] = None
    ):
        """
        Generate a human-readable summary report.

        Args:
            results: List of evaluation results
            output_path: Optional custom output path
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"evaluation_summary_{timestamp}.txt"
        else:
            output_path = Path(output_path)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("VIDEO LLM EVALUATION SUMMARY\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Dataset: {self.dataset_path}\n")
            f.write(f"Total Samples: {len(results)}\n\n")

            # Calculate aggregate metrics
            stats = self._calculate_aggregate_stats(results)

            # Gemini stats
            if "gemini" in stats:
                f.write("=" * 80 + "\n")
                f.write("GEMINI 1.5 PRO RESULTS\n")
                f.write("=" * 80 + "\n\n")
                self._write_model_stats(f, stats["gemini"])

            # GPT-4o stats
            if "gpt4o" in stats:
                f.write("\n" + "=" * 80 + "\n")
                f.write("GPT-4O RESULTS\n")
                f.write("=" * 80 + "\n\n")
                self._write_model_stats(f, stats["gpt4o"])

            # Sample-by-sample comparison
            f.write("\n" + "=" * 80 + "\n")
            f.write("DETAILED RESULTS BY SAMPLE\n")
            f.write("=" * 80 + "\n\n")

            for result in results:
                self._write_sample_details(f, result)

        logger.info(f"Summary report saved to: {output_path}")
        return output_path

    def _calculate_aggregate_stats(self, results: List[Dict]) -> Dict:
        """Calculate aggregate statistics across all results."""
        stats = {"gemini": {}, "gpt4o": {}}

        for model in ["gemini", "gpt4o"]:
            model_results = [r for r in results if f"{model}_metrics" in r]

            if not model_results:
                continue

            # Collect metrics
            metrics_list = [r[f"{model}_metrics"] for r in model_results]

            # Calculate averages
            metric_keys = metrics_list[0].keys() if metrics_list else []
            for key in metric_keys:
                values = [m[key] for m in metrics_list if key in m]
                if values:
                    if isinstance(values[0], bool):
                        stats[model][key] = sum(values) / len(values)
                    else:
                        stats[model][key] = sum(values) / len(values)

            # Classification accuracy
            correct = sum(
                1 for m in metrics_list if m.get("classification_correct", False)
            )
            stats[model]["classification_accuracy"] = (
                correct / len(model_results) if model_results else 0
            )
            stats[model]["total_evaluated"] = len(model_results)

        return stats

    def _write_model_stats(self, f, stats: Dict):
        """Write model statistics to file."""
        f.write(f"Total Evaluated: {stats.get('total_evaluated', 0)}\n\n")

        f.write("Classification Performance:\n")
        f.write(f"  Accuracy: {stats.get('classification_accuracy', 0):.1%}\n\n")

        f.write("Text Similarity Metrics:\n")
        f.write(f"  ROUGE-1:            {stats.get('rouge1', 0):.3f}\n")
        f.write(f"  ROUGE-2:            {stats.get('rouge2', 0):.3f}\n")
        f.write(f"  ROUGE-L:            {stats.get('rougeL', 0):.3f}\n")
        f.write(f"  BLEU:               {stats.get('bleu', 0):.3f}\n")
        f.write(f"  Semantic Similarity: {stats.get('semantic_similarity', 0):.3f}\n\n")

        f.write("Reason Category Performance:\n")
        f.write(f"  Precision: {stats.get('reason_precision', 0):.3f}\n")
        f.write(f"  Recall:    {stats.get('reason_recall', 0):.3f}\n")
        f.write(f"  F1 Score:  {stats.get('reason_f1', 0):.3f}\n")

    def _write_sample_details(self, f, result: Dict):
        """Write detailed results for a single sample."""
        f.write(f"\n{result['sample_id']}\n")
        f.write("-" * 80 + "\n")
        f.write(f"Tweet: {result['tweet_text'][:100]}...\n")
        f.write(f"Human: Misleading={result['human_note']['is_misleading']}\n")

        if "gemini_output" in result:
            gemini = result["gemini_output"]
            if gemini.get("success"):
                f.write(f"Gemini: Misleading={gemini['is_misleading']}")
                if "gemini_metrics" in result:
                    m = result["gemini_metrics"]
                    f.write(
                        f" | Correct={m.get('classification_correct', False)} "
                        f"| Sem={m.get('semantic_similarity', 0):.2f}\n"
                    )
                else:
                    f.write("\n")

        if "gpt4o_output" in result:
            gpt4o = result["gpt4o_output"]
            if gpt4o.get("success"):
                f.write(f"GPT-4o: Misleading={gpt4o['is_misleading']}")
                if "gpt4o_metrics" in result:
                    m = result["gpt4o_metrics"]
                    f.write(
                        f" | Correct={m.get('classification_correct', False)} "
                        f"| Sem={m.get('semantic_similarity', 0):.2f}\n"
                    )
                else:
                    f.write("\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate Video LLMs on misinformation detection"
    )
    parser.add_argument(
        "--dataset",
        default="data/evaluation/dataset.json",
        help="Path to evaluation dataset",
    )
    parser.add_argument(
        "--models",
        default="gemini,gpt4o",
        help="Comma-separated list of models to evaluate (gemini, gpt4o)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of samples to evaluate"
    )
    parser.add_argument("--output", default=None, help="Custom output path for results")
    parser.add_argument(
        "--cache",
        default="data/evaluation/.eval_cache.json",
        help="Cache file for resuming evaluations",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable result caching"
    )

    args = parser.parse_args()

    # Parse models
    models = [m.strip().lower() for m in args.models.split(",")]

    # Initialize evaluator
    evaluator = VideoLLMEvaluator(
        dataset_path=args.dataset,
        cache_file=None if args.no_cache else args.cache,
    )

    # Check which models are available
    available_models = []
    if "gemini" in models:
        if evaluator.gemini.is_available():
            available_models.append("gemini")
            logger.info("✓ Gemini 1.5 Pro available")
        else:
            logger.warning("✗ Gemini API key not found (set GEMINI_API_KEY)")

    if "gpt4o" in models:
        if evaluator.gpt4o.is_available():
            available_models.append("gpt4o")
            logger.info("✓ GPT-4o available")
        else:
            logger.warning("✗ OpenAI API key not found (set OPENAI_API_KEY)")

    if not available_models:
        logger.error("No models available! Set API keys in .env file.")
        return

    # Run evaluation
    logger.info(f"Starting evaluation with: {', '.join(available_models)}")
    results = evaluator.evaluate_all(
        models=available_models,
        limit=args.limit,
        use_cache=not args.no_cache,
    )

    # Save results
    results_path = evaluator.save_results(results, args.output)
    summary_path = evaluator.generate_summary_report(results)

    # Print summary
    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)
    print(f"\n✓ Results saved to: {results_path}")
    print(f"✓ Summary saved to: {summary_path}")
    print(f"\nEvaluated {len(results)} samples with {len(available_models)} model(s)")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

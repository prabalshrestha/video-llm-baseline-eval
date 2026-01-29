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

from scripts.evaluation.llms import GeminiService, GPT4oService, QwenService
from scripts.evaluation.metrics import EvaluationMetrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Model configurations
MODEL_CONFIGS = {
    "gemini": {
        "variants": ["gemini-1.5-pro", "gemini-2.5-flash", "gemini-2.5-pro"],
        "default": "gemini-1.5-pro",
        "service_class": GeminiService,
    },
    "gpt4o": {
        "variants": ["gpt-4o"],
        "default": "gpt-4o",
        "service_class": GPT4oService,
    },
    "qwen": {
        "variants": [
            "qwen2.5-vl-7b-instruct",
            "qwen2.5-vl-32b-instruct",
            "qwen3-vl-8b-thinking",
            "qwen3-vl-32b",
            "qwen3-vl-235b-a22b",
            "qwen3-vl-cloud",
        ],
        "default": "qwen3-vl-cloud",
        "service_class": QwenService,
    },
}


class VideoLLMEvaluator:
    """Main evaluator for testing Video LLMs on misinformation detection."""

    def __init__(
        self,
        dataset_path: str = "data/evaluation/latest/dataset.json",
        output_dir: str = "data/evaluation",
        cache_file: Optional[str] = None,
        model_configs: Optional[Dict] = None,
        create_run_dir: bool = True,
        run_name: Optional[str] = None,
    ):
        """
        Initialize the evaluator.

        Args:
            dataset_path: Path to the evaluation dataset JSON
            output_dir: Directory to save results
            cache_file: Optional path to cache file for resuming evaluations
            model_configs: Optional dict of model configurations {model_family: model_variant}
                          e.g., {"gemini": "gemini-2.0-flash-exp", "qwen": "qwen3-vl-32b"}
            create_run_dir: Whether to create a timestamped run directory (default: True)
            run_name: Optional custom run name (default: timestamp)
        """
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize services with specified model variants
        self.services = {}
        self.model_configs = model_configs or {}

        # Initialize Gemini
        gemini_variant = self.model_configs.get("gemini", "gemini-1.5-pro")
        self.services["gemini"] = GeminiService(model_name=gemini_variant)

        # Initialize GPT-4o
        self.services["gpt4o"] = GPT4oService()

        # Initialize Qwen (support both API and local modes)
        qwen_variant = self.model_configs.get("qwen", "qwen3-vl-cloud")
        use_local = self.model_configs.get("qwen_local", False)
        self.services["qwen"] = QwenService(
            model_name=qwen_variant, use_local=use_local
        )

        self.metrics = EvaluationMetrics()

        # Load dataset
        self.dataset = self._load_dataset()

        # Cache management
        self.cache_file = Path(cache_file) if cache_file else None
        self.cache = self._load_cache()

        # Run directory management
        self.create_run_dir = create_run_dir
        self.run_dir = None
        self.run_name = run_name
        if create_run_dir:
            self.run_dir = self._create_run_directory()

        logger.info(f"Initialized evaluator with {len(self.dataset)} samples")
        logger.info(f"Model configurations: {self.model_configs}")
        if self.run_dir:
            logger.info(f"Run directory: {self.run_dir}")

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

    def _create_run_directory(self) -> Path:
        """
        Create a timestamped run directory with subdirectories.

        Returns:
            Path to the created run directory
        """
        # Generate run name
        if self.run_name:
            run_dir_name = self.run_name
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir_name = f"run_{timestamp}"

        # Create directory structure
        run_dir = self.output_dir / "runs" / run_dir_name
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (run_dir / "models").mkdir(exist_ok=True)
        (run_dir / "metrics").mkdir(exist_ok=True)

        logger.info(f"Created run directory: {run_dir}")
        return run_dir

    def _save_config(self, models: List[str], total_samples: int):
        """
        Save evaluation configuration to config.json.

        Args:
            models: List of models being evaluated
            total_samples: Total number of samples
        """
        if not self.run_dir:
            return

        config = {
            "timestamp": datetime.now().isoformat(),
            "dataset": str(self.dataset_path),
            "models": {},
            "total_samples": total_samples,
            "cache_enabled": bool(self.cache_file),
        }

        # Add model configurations
        for model_name in models:
            if model_name in self.services:
                service = self.services[model_name]
                model_info = {
                    "variant": getattr(service, "model_name", model_name),
                    "api_key_set": service.is_available(),
                }

                # Add Qwen-specific info
                if model_name == "qwen" and hasattr(service, "use_local"):
                    model_info["mode"] = "local" if service.use_local else "api"

                config["models"][model_name] = model_info

        # Save config
        config_path = self.run_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved configuration to: {config_path}")

    def _save_per_model_results(self, results: List[Dict], aggregate_stats: Dict):
        """
        Extract and save individual model results to separate JSON files.

        Args:
            results: List of evaluation results
            aggregate_stats: Aggregate statistics for all models
        """
        if not self.run_dir:
            return

        # Detect which models were evaluated
        evaluated_models = set()
        for result in results:
            for key in result.keys():
                if key.endswith("_output"):
                    model_name = key.replace("_output", "")
                    evaluated_models.add(model_name)

        # Create per-model files
        for model_name in evaluated_models:
            # Get model variant name
            service = self.services.get(model_name)
            model_variant = getattr(service, "model_name", model_name)

            # Extract model-specific results
            model_results = []
            for result in results:
                output_key = f"{model_name}_output"
                metrics_key = f"{model_name}_metrics"

                if output_key in result:
                    model_result = {
                        "sample_id": result["sample_id"],
                        "tweet_id": result.get("tweet_id"),
                        "tweet_url": result.get("tweet_url"),
                        "video_path": result.get("video_path"),
                        "tweet_text": result.get("tweet_text"),
                        "human_note": result.get("human_note"),
                        "output": result[output_key],
                        "response_time_seconds": result[output_key].get(
                            "response_time_seconds"
                        ),
                    }

                    if metrics_key in result:
                        model_result["metrics"] = result[metrics_key]

                    model_results.append(model_result)

            # Prepare per-model JSON
            per_model_data = {
                "model_info": {
                    "model_name": model_variant,
                    "model_family": model_name,
                    "timestamp": datetime.now().isoformat(),
                },
                "aggregate_metrics": aggregate_stats.get(model_name, {}),
                "results": model_results,
            }

            # Save to file
            filename = f"{model_variant}.json"
            model_path = self.run_dir / "models" / filename
            with open(model_path, "w", encoding="utf-8") as f:
                json.dump(per_model_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {model_name} results to: {model_path}")

    def _save_comparison_table(self, aggregate_stats: Dict):
        """
        Generate and save CSV comparison table.

        Args:
            aggregate_stats: Aggregate statistics for all models
        """
        if not self.run_dir:
            return

        import csv

        # Prepare CSV data
        csv_path = self.run_dir / "metrics" / "comparison_table.csv"

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(
                [
                    "Model",
                    "Accuracy",
                    "ROUGE-1",
                    "ROUGE-2",
                    "ROUGE-L",
                    "BLEU",
                    "Semantic Sim",
                    "Reason F1",
                    "Avg Time (s)",
                    "Samples",
                ]
            )

            # Write data for each model
            for model_name, stats in aggregate_stats.items():
                if not stats:
                    continue

                # Get model variant name
                service = self.services.get(model_name)
                model_variant = getattr(service, "model_name", model_name)

                writer.writerow(
                    [
                        model_variant,
                        f"{stats.get('classification_accuracy', 0):.3f}",
                        f"{stats.get('rouge1', 0):.3f}",
                        f"{stats.get('rouge2', 0):.3f}",
                        f"{stats.get('rougeL', 0):.3f}",
                        f"{stats.get('bleu', 0):.3f}",
                        f"{stats.get('semantic_similarity', 0):.3f}",
                        f"{stats.get('reason_f1', 0):.3f}",
                        f"{stats.get('avg_response_time', 0):.2f}",
                        stats.get("total_evaluated", 0),
                    ]
                )

        logger.info(f"Saved comparison table to: {csv_path}")

    def _update_latest_symlink(self):
        """Update the 'latest' symlink to point to the current run directory."""
        if not self.run_dir:
            return

        latest_link = self.output_dir / "runs" / "latest"

        # Remove existing symlink if it exists
        try:
            if latest_link.is_symlink():
                latest_link.unlink()
            elif latest_link.exists():
                # It's a directory or file, not a symlink - remove it
                import shutil

                if latest_link.is_dir():
                    shutil.rmtree(latest_link)
                else:
                    latest_link.unlink()
        except Exception as e:
            logger.warning(f"Could not remove existing 'latest' link: {e}")

        # Create new symlink (use relative path for portability)
        try:
            latest_link.symlink_to(self.run_dir.name)
            logger.info(f"Updated 'latest' symlink to: {self.run_dir.name}")
        except Exception as e:
            logger.warning(
                f"Could not create symlink (may not be supported on this OS): {e}"
            )

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
            models: List of models to use ('gemini', 'gpt4o', 'qwen')
            use_cache: Whether to use cached results

        Returns:
            Dictionary with evaluation results
        """
        sample_id = sample["metadata"]["sample_id"]
        video_path = sample["video"]["path"]
        tweet_text = sample["tweet"]["text"]
        author_name = sample["tweet"]["author_name"]
        author_username = sample["tweet"].get("author_username")
        tweet_created_at = sample["tweet"].get("created_at")

        # Get first community note (dataset has array of notes)
        community_notes = sample.get("community_notes", [])
        if not community_notes:
            logger.warning(f"No community notes found for {sample_id}, skipping")
            return None

        human_note = community_notes[0]  # Use first note for evaluation

        result = {
            "sample_id": sample_id,
            "tweet_id": sample["tweet"]["tweet_id"],
            "tweet_url": sample["tweet"]["url"],
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

        # Evaluate with each requested model
        for model_name in models:
            if model_name not in self.services:
                logger.warning(f"Unknown model: {model_name}")
                continue

            service = self.services[model_name]

            if service.is_available():
                logger.info(f"Evaluating {sample_id} with {model_name}...")
                try:
                    import time

                    start_time = time.time()

                    output = service.analyze_video(
                        video_path,
                        tweet_text,
                        author_name,
                        author_username,
                        tweet_created_at,
                    )

                    elapsed_time = time.time() - start_time
                    output["response_time_seconds"] = round(elapsed_time, 2)

                    result[f"{model_name}_output"] = output
                    logger.info(f"  Completed in {elapsed_time:.2f}s")

                    # Calculate metrics
                    if output.get("success"):
                        metrics = self.metrics.compare_outputs(output, human_note)
                        result[f"{model_name}_metrics"] = metrics
                except Exception as e:
                    logger.error(f"Error evaluating with {model_name}: {e}")
                    result[f"{model_name}_output"] = {
                        "success": False,
                        "error": str(e),
                        "model": model_name,
                    }
            else:
                logger.warning(f"{model_name} not available - skipping")

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
                if result is not None:  # Skip samples with no community notes
                    results.append(result)
            except Exception as e:
                logger.error(f"Error evaluating {sample['metadata']['sample_id']}: {e}")
                import traceback

                logger.debug(traceback.format_exc())
                # Continue with next sample

        return results

    def save_results(
        self,
        results: List[Dict],
        output_path: Optional[str] = None,
        save_per_model: bool = True,
    ):
        """
        Save evaluation results to JSON file.

        Args:
            results: List of evaluation results
            output_path: Optional custom output path (disables run directory structure)
            save_per_model: Whether to save individual model files (default: True)
        """
        # Calculate aggregate statistics
        aggregate_stats = self._calculate_aggregate_stats(results)

        # Determine output path
        if output_path is not None:
            # Custom output path specified - use old behavior
            output_path = Path(output_path)
        elif self.run_dir:
            # Use run directory structure
            output_path = self.run_dir / "unified_results.json"
        else:
            # Fallback to old behavior
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"llm_results_{timestamp}.json"

        # Prepare output
        output_data = {
            "evaluation_info": {
                "timestamp": datetime.now().isoformat(),
                "dataset": str(self.dataset_path),
                "total_samples": len(results),
            },
            "results": results,
            "aggregate_metrics": aggregate_stats,
        }

        # Save unified results file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to: {output_path}")

        # Save per-model files if using run directory
        if self.run_dir and save_per_model:
            self._save_per_model_results(results, aggregate_stats)

        # Save aggregate stats separately
        if self.run_dir:
            stats_path = self.run_dir / "metrics" / "aggregate_stats.json"
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(aggregate_stats, f, indent=2, ensure_ascii=False)
            logger.info(f"Aggregate stats saved to: {stats_path}")

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
        # Determine output path
        if output_path is not None:
            output_path = Path(output_path)
        elif self.run_dir:
            output_path = self.run_dir / "summary_report.txt"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"evaluation_summary_{timestamp}.txt"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("VIDEO LLM EVALUATION SUMMARY\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Dataset: {self.dataset_path}\n")
            f.write(f"Total Samples: {len(results)}\n\n")

            # Calculate aggregate metrics
            stats = self._calculate_aggregate_stats(results)

            # Write stats for each model
            for model_name, model_stats in stats.items():
                if model_stats:
                    f.write("=" * 80 + "\n")
                    f.write(f"{model_name.upper()} RESULTS\n")
                    f.write("=" * 80 + "\n\n")
                    self._write_model_stats(f, model_stats)

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
        # Detect which models were used
        all_models = set()
        for result in results:
            for key in result.keys():
                if key.endswith("_metrics"):
                    model_name = key.replace("_metrics", "")
                    all_models.add(model_name)

        stats = {model: {} for model in all_models}

        for model in all_models:
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

            # Response time statistics
            response_times = [
                r[f"{model}_output"].get("response_time_seconds", 0)
                for r in model_results
                if f"{model}_output" in r
                and r[f"{model}_output"].get("response_time_seconds")
            ]
            if response_times:
                stats[model]["avg_response_time"] = sum(response_times) / len(
                    response_times
                )
                stats[model]["min_response_time"] = min(response_times)
                stats[model]["max_response_time"] = max(response_times)
                stats[model]["total_response_time"] = sum(response_times)

        return stats

    def _write_model_stats(self, f, stats: Dict):
        """Write model statistics to file."""
        f.write(f"Total Evaluated: {stats.get('total_evaluated', 0)}\n\n")

        f.write("Classification Performance:\n")
        f.write(f"  Accuracy: {stats.get('classification_accuracy', 0):.1%}\n\n")

        # Response time statistics
        if "avg_response_time" in stats:
            f.write("Response Time Performance:\n")
            f.write(f"  Average: {stats.get('avg_response_time', 0):.2f}s\n")
            f.write(f"  Min:     {stats.get('min_response_time', 0):.2f}s\n")
            f.write(f"  Max:     {stats.get('max_response_time', 0):.2f}s\n")
            f.write(f"  Total:   {stats.get('total_response_time', 0):.2f}s\n\n")

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

        # Write output for each model that was evaluated
        for key in result.keys():
            if key.endswith("_output"):
                model_name = key.replace("_output", "")
                output = result[key]

                if output.get("success"):
                    f.write(
                        f"{model_name.capitalize()}: Misleading={output['is_misleading']}"
                    )

                    metrics_key = f"{model_name}_metrics"
                    if metrics_key in result:
                        m = result[metrics_key]
                        f.write(
                            f" | Correct={m.get('classification_correct', False)} "
                            f"| Sem={m.get('semantic_similarity', 0):.2f}"
                        )

                    # Add response time
                    if output.get("response_time_seconds"):
                        f.write(f" | Time={output['response_time_seconds']:.2f}s")

                    f.write("\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate Video LLMs on misinformation detection"
    )
    parser.add_argument(
        "--dataset",
        default="data/evaluation/latest/dataset.json",
        help="Path to evaluation dataset (default: latest symlink)",
    )
    parser.add_argument(
        "--models",
        default="gemini,gpt4o",
        help="Comma-separated list of models to evaluate (gemini, gpt4o, qwen)",
    )
    parser.add_argument(
        "--gemini-model",
        default="gemini-1.5-pro",
        choices=MODEL_CONFIGS["gemini"]["variants"],
        help="Gemini model variant to use",
    )
    parser.add_argument(
        "--qwen-model",
        default="qwen2.5-vl-7b-instruct",
        choices=MODEL_CONFIGS["qwen"]["variants"],
        help="Qwen model variant to use",
    )
    parser.add_argument(
        "--qwen-local",
        action="store_true",
        help="Use local Qwen inference instead of API",
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
    parser.add_argument(
        "--run-name",
        default=None,
        help="Custom run name (default: auto-generated timestamp)",
    )
    parser.add_argument(
        "--no-per-model-files",
        action="store_true",
        help="Skip generating individual model files (faster)",
    )

    args = parser.parse_args()

    # Parse models
    models = [m.strip().lower() for m in args.models.split(",")]

    # Build model configurations
    model_configs = {
        "gemini": args.gemini_model,
        "qwen": args.qwen_model,
        "qwen_local": args.qwen_local,
    }

    # Determine if we should create run directory (disabled if custom output specified)
    create_run_dir = args.output is None

    # Initialize evaluator
    evaluator = VideoLLMEvaluator(
        dataset_path=args.dataset,
        cache_file=None if args.no_cache else args.cache,
        model_configs=model_configs,
        create_run_dir=create_run_dir,
        run_name=args.run_name,
    )

    # Check which models are available
    available_models = []
    for model in models:
        if model in evaluator.services:
            service = evaluator.services[model]
            if service.is_available():
                available_models.append(model)
                variant = getattr(service, "model_name", model)
                logger.info(f"✓ {model.upper()} available: {variant}")
            else:
                logger.warning(
                    f"✗ {model.upper()} not available (check API key or setup)"
                )
        else:
            logger.warning(f"✗ Unknown model: {model}")

    if not available_models:
        logger.error(
            "No models available! Set API keys in .env file or configure local models."
        )
        logger.info("\nTo enable models:")
        logger.info("  Gemini: Set GEMINI_API_KEY environment variable")
        logger.info("  GPT-4o: Set OPENAI_API_KEY environment variable")
        logger.info(
            "  Qwen API: Set QWEN_API_KEY or DASHSCOPE_API_KEY environment variable"
        )
        logger.info(
            "  Qwen Local: Install torch, transformers, qwen-vl-utils and use --qwen-local"
        )
        return

    # Run evaluation
    logger.info(f"Starting evaluation with: {', '.join(available_models)}")
    results = evaluator.evaluate_all(
        models=available_models,
        limit=args.limit,
        use_cache=not args.no_cache,
    )

    # Save configuration
    evaluator._save_config(available_models, len(results))

    # Save results
    save_per_model = not args.no_per_model_files
    results_path = evaluator.save_results(results, args.output, save_per_model)
    summary_path = evaluator.generate_summary_report(results)

    # Save comparison table and update symlink
    if evaluator.run_dir:
        aggregate_stats = evaluator._calculate_aggregate_stats(results)
        evaluator._save_comparison_table(aggregate_stats)
        evaluator._update_latest_symlink()

    # Print summary
    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)
    print(f"\n✓ Results saved to: {results_path}")
    print(f"✓ Summary saved to: {summary_path}")
    if evaluator.run_dir:
        print(f"✓ Run directory: {evaluator.run_dir}")
        if save_per_model:
            print(f"✓ Per-model files: {evaluator.run_dir / 'models'}")
        print(
            f"✓ Comparison table: {evaluator.run_dir / 'metrics' / 'comparison_table.csv'}"
        )
    print(f"\nEvaluated {len(results)} samples with {len(available_models)} model(s)")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

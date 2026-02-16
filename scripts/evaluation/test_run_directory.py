#!/usr/bin/env python3
"""
Test script for verifying run directory structure implementation.
Tests the hybrid evaluation output structure without running actual evaluations.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
import tempfile
import shutil
from datetime import datetime


# Mock the services to avoid requiring API keys
class MockService:
    def __init__(self, model_name="mock-model"):
        self.model_name = model_name

    def is_available(self):
        return True

    def analyze_video(
        self,
        video_path,
        tweet_text,
        author_name,
        author_username=None,
        tweet_created_at=None,
    ):
        return {
            "success": True,
            "model": self.model_name,
            "is_misleading": True,
            "summary": "Test summary",
            "misleading_tags": ["test_reason"],
            "confidence": "high",
            "raw_response": "test response",
        }


def test_run_directory_structure():
    """Test that run directory structure is created correctly."""
    print("Testing Run Directory Structure")
    print("=" * 70)

    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create mock dataset
        dataset_path = temp_path / "dataset.json"
        mock_dataset = {
            "samples": [
                {
                    "metadata": {"sample_id": "test_001"},
                    "video": {"path": "/tmp/test.mp4"},
                    "tweet": {
                        "text": "Test tweet",
                        "author_name": "Test Author",
                        "author_username": "testuser",
                    },
                    "community_note": {
                        "is_misleading": True,
                        "summary": "Test note",
                        "misleading_tags": ["test"],
                    },
                }
            ]
        }

        with open(dataset_path, "w") as f:
            json.dump(mock_dataset, f)

        # Import evaluator (this should work now)
        from scripts.evaluation.evaluate_models import VideoLLMEvaluator

        # Test 1: Create evaluator with run directory
        print("\n1. Testing run directory creation...")
        evaluator = VideoLLMEvaluator(
            dataset_path=str(dataset_path),
            output_dir=str(temp_path / "output"),
            cache_file=None,
            create_run_dir=True,
            run_name="test_run",
        )

        # Verify run directory was created
        assert evaluator.run_dir is not None
        assert evaluator.run_dir.exists()
        assert (evaluator.run_dir / "models").exists()
        assert (evaluator.run_dir / "metrics").exists()
        print(f"   ✓ Run directory created: {evaluator.run_dir}")

        # Test 2: Mock services
        print("\n2. Testing with mock services...")
        evaluator.services = {
            "mock1": MockService("mock-model-1"),
            "mock2": MockService("mock-model-2"),
        }

        # Create mock results
        mock_results = [
            {
                "sample_id": "test_001",
                "video_path": "/tmp/test.mp4",
                "tweet_text": "Test tweet",
                "human_note": {
                    "is_misleading": True,
                    "summary": "Test",
                    "misleading_tags": ["test"],
                },
                "mock1_output": {
                    "success": True,
                    "is_misleading": True,
                    "summary": "Test summary 1",
                    "misleading_tags": ["test"],
                    "confidence": "high",
                },
                "mock1_metrics": {
                    "classification_correct": True,
                    "rouge1": 0.75,
                    "rouge2": 0.60,
                    "rougeL": 0.70,
                    "bleu": 0.65,
                    "semantic_similarity": 0.85,
                    "reason_f1": 0.80,
                },
                "mock2_output": {
                    "success": True,
                    "is_misleading": False,
                    "summary": "Test summary 2",
                    "misleading_tags": [],
                    "confidence": "medium",
                },
                "mock2_metrics": {
                    "classification_correct": False,
                    "rouge1": 0.60,
                    "rouge2": 0.45,
                    "rougeL": 0.55,
                    "bleu": 0.50,
                    "semantic_similarity": 0.70,
                    "reason_f1": 0.65,
                },
            }
        ]

        # Test 3: Save config
        print("\n3. Testing config save...")
        evaluator._save_config(["mock1", "mock2"], len(mock_results))
        config_path = evaluator.run_dir / "config.json"
        assert config_path.exists()
        with open(config_path) as f:
            config = json.load(f)
        assert "timestamp" in config
        assert "models" in config
        assert "mock1" in config["models"]
        print(f"   ✓ Config saved: {config_path}")

        # Test 4: Save results
        print("\n4. Testing results save...")
        results_path = evaluator.save_results(mock_results)
        assert results_path.exists()
        with open(results_path) as f:
            results_data = json.load(f)
        assert "evaluation_info" in results_data
        assert "results" in results_data
        assert "aggregate_metrics" in results_data
        print(f"   ✓ Results saved: {results_path}")

        # Test 5: Verify per-model files
        print("\n5. Testing per-model files...")
        model1_path = evaluator.run_dir / "models" / "mock-model-1.json"
        model2_path = evaluator.run_dir / "models" / "mock-model-2.json"
        assert model1_path.exists()
        assert model2_path.exists()
        with open(model1_path) as f:
            model1_data = json.load(f)
        assert "model_info" in model1_data
        assert "aggregate_metrics" in model1_data
        assert "results" in model1_data
        print(f"   ✓ Per-model files created:")
        print(f"     - {model1_path}")
        print(f"     - {model2_path}")

        # Test 6: Save summary report
        print("\n6. Testing summary report...")
        summary_path = evaluator.generate_summary_report(mock_results)
        assert summary_path.exists()
        print(f"   ✓ Summary report saved: {summary_path}")

        # Test 7: Verify comparison table
        print("\n7. Testing comparison table...")
        aggregate_stats = evaluator._calculate_aggregate_stats(mock_results)
        evaluator._save_comparison_table(aggregate_stats)
        csv_path = evaluator.run_dir / "metrics" / "comparison_table.csv"
        assert csv_path.exists()
        with open(csv_path) as f:
            csv_content = f.read()
        assert "Model,Accuracy" in csv_content
        assert "mock-model-1" in csv_content
        assert "mock-model-2" in csv_content
        print(f"   ✓ Comparison table saved: {csv_path}")

        # Test 8: Verify aggregate stats
        print("\n8. Testing aggregate stats...")
        stats_path = evaluator.run_dir / "metrics" / "aggregate_stats.json"
        assert stats_path.exists()
        with open(stats_path) as f:
            stats_data = json.load(f)
        assert "mock1" in stats_data
        assert "mock2" in stats_data
        print(f"   ✓ Aggregate stats saved: {stats_path}")

        # Test 9: Update symlink
        print("\n9. Testing latest symlink...")
        evaluator._update_latest_symlink()
        latest_link = evaluator.output_dir / "runs" / "latest"
        # Symlink may not work on all platforms, so just check it was attempted
        print(f"   ✓ Latest symlink attempted: {latest_link}")

        # Test 10: Verify directory structure
        print("\n10. Verifying complete directory structure...")
        expected_files = [
            "config.json",
            "unified_results.json",
            "summary_report.txt",
            "models/mock-model-1.json",
            "models/mock-model-2.json",
            "metrics/comparison_table.csv",
            "metrics/aggregate_stats.json",
        ]

        for expected_file in expected_files:
            file_path = evaluator.run_dir / expected_file
            assert file_path.exists(), f"Missing file: {expected_file}"
            print(f"   ✓ {expected_file}")

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✅")
        print("=" * 70)

        # Print directory tree
        print("\nGenerated Directory Structure:")
        print_directory_tree(evaluator.run_dir, prefix="")


def print_directory_tree(path: Path, prefix: str = ""):
    """Print directory tree structure."""
    if path.is_file():
        size = path.stat().st_size
        print(f"{prefix}├── {path.name} ({size} bytes)")
    elif path.is_dir():
        print(f"{prefix}├── {path.name}/")
        items = sorted(path.iterdir())
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_directory_tree(item, new_prefix)


if __name__ == "__main__":
    try:
        test_run_directory_structure()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

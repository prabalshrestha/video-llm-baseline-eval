#!/usr/bin/env python3
"""
Main entry point for Video LLM Baseline Evaluation.

Usage:
    python main.py download              # Download & filter Community Notes
    python main.py filter                # Identify actual video notes (checks media type)
    python main.py videos --limit 30     # Download videos
    python main.py dataset               # Create evaluation dataset
    python main.py evaluate              # Evaluate Video LLMs
    python main.py pipeline              # Run full pipeline
    python main.py explore               # Explore data
    python main.py test                  # Test setup
"""

import sys
import argparse
import subprocess
from pathlib import Path


class VideoLLMCLI:
    """Command-line interface for Video LLM project."""

    def __init__(self):
        self.project_root = Path(__file__).parent

    def run_script(self, script_path, args=None):
        """Run a Python script."""
        cmd = [sys.executable, str(self.project_root / script_path)]
        if args:
            cmd.extend(args)

        print(f"\n{'='*70}")
        print(f"▶ Running: {script_path}")
        print(f"{'='*70}\n")

        try:
            subprocess.run(cmd, check=True)
            print(f"\n✓ {script_path} completed successfully\n")
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n✗ {script_path} failed with error code {e.returncode}\n")
            return False

    def download(self):
        """Download and filter Community Notes data."""
        return self.run_script("scripts/data_processing/download_notes.py")

    def filter(self, sample=None):
        """Identify actual video notes by checking media type."""
        args = ["--sample", str(sample)] if sample else []
        return self.run_script("scripts/data_processing/identify_video_notes.py", args)

    def videos(self, limit=30, random_sample=False, seed=42):
        """Download videos."""
        args = ["--limit", str(limit)]
        if random_sample:
            args.append("--random")
            args.extend(["--seed", str(seed)])
        return self.run_script("scripts/data_processing/download_videos.py", args)

    def dataset(self, use_api=True, sample_size=None, seed=42):
        """Create complete evaluation dataset."""
        args = []
        if not use_api:
            args.append("--no-api")
        if sample_size:
            args.extend(["--sample-size", str(sample_size)])
            args.extend(["--random-seed", str(seed)])
        return self.run_script("scripts/data_processing/create_dataset.py", args)

    def evaluate(self, models="gemini,gpt4o", limit=None):
        """Evaluate Video LLMs on the dataset."""
        args = ["--models", models]
        if limit:
            args.extend(["--limit", str(limit)])
        return self.run_script("scripts/evaluation/evaluate_models.py", args)

    def pipeline(self, video_limit=30, use_api=True, random_sample=False, seed=42):
        """Run the complete data collection pipeline."""
        print("\n" + "=" * 70)
        print("VIDEO LLM BASELINE EVALUATION - FULL PIPELINE")
        print("=" * 70)
        print(f"\nThis will run the complete pipeline with {video_limit} videos.")
        if random_sample:
            print(f"Random sampling enabled (seed: {seed})")
        print()

        steps = [
            ("Download Community Notes", self.download),
            ("Filter for Videos", self.filter),
            ("Download Videos", lambda: self.videos(video_limit, random_sample, seed)),
            ("Create Dataset", lambda: self.dataset(use_api)),
        ]

        completed = 0
        for i, (name, func) in enumerate(steps, 1):
            print(f"\n[Step {i}/{len(steps)}] {name}")
            if func():
                completed += 1
            else:
                print(f"\n✗ Pipeline stopped at step {i}")
                break

        print("\n" + "=" * 70)
        print("PIPELINE SUMMARY")
        print("=" * 70)
        print(f"Completed: {completed}/{len(steps)} steps")

        if completed == len(steps):
            print("\n✓ Pipeline completed successfully!")
            self.show_results()
        else:
            print(f"\n⚠ Pipeline incomplete")

    def explore(self):
        """Explore the data."""
        return self.run_script("scripts/data_processing/explore_notes.py")
    
    def random_sample(self, limit=30, seed=None, status="CURRENTLY_RATED_HELPFUL"):
        """Random sample notes by status, download videos, and create dataset."""
        args = ["--limit", str(limit)]
        if seed is not None:
            args.extend(["--seed", str(seed)])
        if status:
            args.extend(["--status", status])
        return self.run_script("scripts/data_processing/random_sample_pipeline.py", args)

    def test(self):
        """Test environment setup."""
        return self.run_script("test_setup.py")

    def show_results(self):
        """Show summary of collected data."""
        print("\n" + "=" * 70)
        print("📊 DATA SUMMARY")
        print("=" * 70)

        # Check for data files
        data_dir = self.project_root / "data"

        # Raw data
        notes_file = data_dir / "raw" / "notes-00000.tsv"
        if notes_file.exists():
            print(f"\n✓ Raw Community Notes: {notes_file}")

        # Filtered data
        media_file = data_dir / "filtered" / "media_notes.csv"
        if media_file.exists():
            import pandas as pd

            df = pd.read_csv(media_file)
            print(f"✓ Media Notes: {len(df):,} notes")

        video_file = data_dir / "filtered" / "verified_video_notes.csv"
        if video_file.exists():
            import pandas as pd

            df = pd.read_csv(video_file)
            print(f"✓ Verified Video Notes: {len(df):,} notes")

        # Videos
        videos_dir = data_dir / "videos"
        if videos_dir.exists():
            mp4_files = list(videos_dir.glob("*.mp4"))
            print(f"✓ Downloaded Videos: {len(mp4_files)} files")

            mapping_file = videos_dir / "video_notes_mapping.json"
            if mapping_file.exists():
                print(f"✓ Video Mappings: {mapping_file.name}")

        print("\n" + "=" * 70)

    def show_help(self):
        """Show available commands."""
        print("\n" + "=" * 70)
        print("VIDEO LLM BASELINE EVALUATION - Commands")
        print("=" * 70)
        print(
            """
Available Commands:

  python main.py download                    Download & filter Community Notes
  python main.py filter [--sample N]         Identify actual video notes (checks media type)  
  python main.py videos [--limit N]          Download N videos (default: 30)
  python main.py dataset                     Create evaluation dataset ⭐
  python main.py evaluate [OPTIONS]          Evaluate Video LLMs 🎯
  python main.py pipeline [--limit N]        Run full pipeline (default: 30 videos)
  python main.py random [--limit N]          🎲 Random sample helpful notes + videos 🎲
  python main.py explore                     Explore collected data
  python main.py test                        Test environment setup
  python main.py status                      Show data summary
  python main.py help                        Show this help

Random Sampling Options (ALL COMMANDS):

  --random              Enable random sampling for video selection
  --seed N              Random seed for reproducibility (default: 42)
  --sample-size N       Sample size for dataset creation
  
  Works with: pipeline, videos, dataset, random commands
  
  Examples:
    python main.py pipeline --limit 50 --random --seed 42
    python main.py videos --limit 30 --random
    python main.py dataset --sample-size 100 --seed 42

Random Sample Command (Quick Start):

  python main.py random [--limit N] [--seed S] [--status STATUS]
  
  Randomly samples tweets with notes of specified status, downloads videos,
  and creates evaluation dataset. Maximum randomness for diverse sampling!
  
  Options:
    --limit N     Number of videos to download (default: 30)
    --seed S      Random seed for reproducibility (default: 42)
    --status STR  Note status filter (default: CURRENTLY_RATED_HELPFUL)
                  Other options: CURRENTLY_RATED_NOT_HELPFUL, NEEDS_MORE_RATINGS
  
  Examples:
    python main.py random --limit 50                           # 50 helpful videos
    python main.py random --limit 30 --seed 42                 # Reproducible
    python main.py random --limit 20 --status NEEDS_MORE_RATINGS  # Unrated notes
    python main.py random --limit 40 --status CURRENTLY_RATED_NOT_HELPFUL  # Not helpful

Evaluation Options:

  --models MODEL1,MODEL2    Models to evaluate (gemini, gpt4o)
  --limit N                 Evaluate only first N samples

Examples:

  # Quick start - random sample 30 helpful videos
  python main.py random --limit 30

  # Run complete pipeline with random sampling
  python main.py pipeline --limit 50 --random --seed 42

  # Run pipeline without random sampling (sequential)
  python main.py pipeline --limit 30

  # Download videos with random sampling
  python main.py videos --limit 30 --random --seed 123

  # Create dataset with random sampling
  python main.py dataset --sample-size 100 --seed 42

  # Test video identification with sample
  python main.py filter --sample 100

  # Identify all videos (takes ~6 hours for 122K notes)
  python main.py filter

  # Create dataset and evaluate with both models
  python main.py dataset
  python main.py evaluate

  # Evaluate with only Gemini on 5 videos
  python main.py evaluate --models gemini --limit 5

  # Evaluate with both models
  python main.py evaluate --models gemini,gpt4o

  # Download 50 videos, create dataset, then evaluate
  python main.py videos --limit 50
  python main.py dataset
  python main.py evaluate --limit 10

  # Check what you have
  python main.py status

  # Step by step workflow with random sampling
  python main.py download
  python main.py filter
  python main.py videos --limit 30 --random --seed 42
  python main.py dataset
  python main.py evaluate

API Keys Setup (Required for evaluation):

  Create a .env file with:
    GEMINI_API_KEY=your_key_here          # Get at: https://ai.google.dev/
    OPENAI_API_KEY=your_key_here          # Get at: https://platform.openai.com/

  Optional:
    TWITTER_BEARER_TOKEN=your_key_here    # For complete tweet data

Note: At least one Video LLM API key is required for evaluation.
"""
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Video LLM Baseline Evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=[
            "download",
            "filter",
            "videos",
            "dataset",
            "evaluate",
            "pipeline",
            "random",
            "explore",
            "test",
            "status",
            "help",
        ],
        default="help",
        help="Command to run",
    )

    parser.add_argument(
        "--limit", type=int, default=30, help="Number of videos to download/evaluate"
    )

    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Number of media notes to check (for filter command only)",
    )

    parser.add_argument(
        "--models",
        type=str,
        default="gemini,gpt4o",
        help="Models to evaluate (comma-separated: gemini, gpt4o)",
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (default: random based on timestamp)",
    )
    
    parser.add_argument(
        "--random",
        action="store_true",
        help="Enable random sampling for videos (pipeline/videos commands)",
    )
    
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Sample size for dataset creation (dataset command)",
    )
    
    parser.add_argument(
        "--status",
        type=str,
        default="CURRENTLY_RATED_HELPFUL",
        help="Note status filter for random command (default: CURRENTLY_RATED_HELPFUL)",
    )

    args = parser.parse_args()

    cli = VideoLLMCLI()

    # Route commands
    commands = {
        "download": cli.download,
        "filter": lambda: cli.filter(args.sample),
        "videos": lambda: cli.videos(args.limit, args.random, args.seed),
        "dataset": lambda: cli.dataset(sample_size=args.sample_size, seed=args.seed),
        "evaluate": lambda: cli.evaluate(args.models, args.limit),
        "pipeline": lambda: cli.pipeline(args.limit, random_sample=args.random, seed=args.seed),
        "random": lambda: cli.random_sample(args.limit, args.seed, args.status),
        "explore": cli.explore,
        "test": cli.test,
        "status": cli.show_results,
        "help": cli.show_help,
    }

    if args.command in commands:
        commands[args.command]()
    else:
        cli.show_help()


if __name__ == "__main__":
    main()

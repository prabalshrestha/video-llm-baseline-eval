#!/usr/bin/env python3
"""
Main entry point for Video LLM Baseline Evaluation.

Usage:
    python main.py download              # Download & filter Community Notes
    python main.py filter                # Filter for video notes
    python main.py videos --limit 30     # Download videos
    python main.py mapping               # Create mappings
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

    def filter(self):
        """Filter for likely video notes."""
        return self.run_script("scripts/data_processing/filter_video_notes.py")

    def videos(self, limit=30):
        """Download videos."""
        args = ["--limit", str(limit)]
        return self.run_script("scripts/data_processing/download_videos.py", args)

    def dataset(self, use_api=True):
        """Create complete evaluation dataset."""
        args = ["--no-api"] if not use_api else []
        return self.run_script("scripts/data_processing/create_dataset.py", args)

    def pipeline(self, video_limit=30, use_api=True):
        """Run the complete data collection pipeline."""
        print("\n" + "=" * 70)
        print("VIDEO LLM BASELINE EVALUATION - FULL PIPELINE")
        print("=" * 70)
        print(f"\nThis will run the complete pipeline with {video_limit} videos.\n")

        steps = [
            ("Download Community Notes", self.download),
            ("Filter for Videos", self.filter),
            ("Download Videos", lambda: self.videos(video_limit)),
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

        video_file = data_dir / "filtered" / "likely_video_notes.csv"
        if video_file.exists():
            import pandas as pd

            df = pd.read_csv(video_file)
            print(f"✓ Likely Video Notes: {len(df):,} notes")

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

  python main.py download              Download & filter Community Notes
  python main.py filter                Filter for likely video notes  
  python main.py videos [--limit N]    Download N videos (default: 30)
  python main.py dataset               Create evaluation dataset ⭐
  python main.py pipeline [--limit N]  Run full pipeline (default: 30 videos)
  python main.py explore               Explore collected data
  python main.py test                  Test environment setup
  python main.py status                Show data summary
  python main.py help                  Show this help

Examples:

  # Quick start - run everything
  python main.py pipeline

  # Just create dataset from existing data
  python main.py dataset

  # Download 50 videos then create dataset
  python main.py videos --limit 50
  python main.py dataset

  # Check what you have
  python main.py status

  # Step by step
  python main.py download
  python main.py filter
  python main.py videos --limit 30
  python main.py dataset

Note: Dataset creation automatically uses Twitter API if credentials are available.
      Add TWITTER_BEARER_TOKEN to .env for complete tweet data.
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
            "pipeline",
            "explore",
            "test",
            "status",
            "help",
        ],
        default="help",
        help="Command to run",
    )

    parser.add_argument(
        "--limit", type=int, default=30, help="Number of videos to download"
    )

    args = parser.parse_args()

    cli = VideoLLMCLI()

    # Route commands
    commands = {
        "download": cli.download,
        "filter": cli.filter,
        "videos": lambda: cli.videos(args.limit),
        "dataset": cli.dataset,
        "pipeline": cli.pipeline,
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

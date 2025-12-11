"""
Download Sample Videos from Twitter
Downloads videos from verified_video_notes.csv (or likely_video_notes.csv as fallback) using yt-dlp.
For best results, run identify_video_notes.py first to get accurate video filtering.
"""

import pandas as pd
from pathlib import Path
import logging
import subprocess
import json
import time

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VideoDownloader:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.filtered_dir = self.data_dir / "filtered"
        self.videos_dir = self.data_dir / "videos"
        self.videos_dir.mkdir(exist_ok=True)

        # Create metadata file
        self.metadata = []
        self.metadata_file = self.videos_dir / "downloaded_videos.json"

    def check_ytdlp(self):
        """Check if yt-dlp is installed."""
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                logger.info(f"✓ yt-dlp version: {result.stdout.strip()}")
                return True
            return False
        except FileNotFoundError:
            logger.error("yt-dlp not found!")
            logger.info("\nTo install yt-dlp:")
            logger.info("  pip install yt-dlp")
            logger.info("  or: brew install yt-dlp (on macOS)")
            return False
        except Exception as e:
            logger.error(f"Error checking yt-dlp: {e}")
            return False

    def load_video_notes(self, limit=None, use_verified=True):
        """Load video notes from CSV.
        
        Args:
            limit: Number of notes to load
            use_verified: If True, use verified_video_notes.csv (accurate),
                         if False, use likely_video_notes.csv (keyword-based)
        """
        if use_verified:
            filepath = self.filtered_dir / "verified_video_notes.csv"
            if not filepath.exists():
                logger.warning("verified_video_notes.csv not found, falling back to likely_video_notes.csv")
                logger.warning("Run identify_video_notes.py first for accurate filtering!")
                filepath = self.filtered_dir / "likely_video_notes.csv"
        else:
            filepath = self.filtered_dir / "likely_video_notes.csv"

        try:
            df = pd.read_csv(filepath)
            logger.info(f"Loaded {len(df)} video notes from {filepath.name}")

            if limit:
                df = df.head(limit)
                logger.info(f"Limited to first {limit} notes")

            return df
        except Exception as e:
            logger.error(f"Failed to load video notes: {e}")
            return None

    def download_video(self, tweet_id, index):
        """Download a single video using yt-dlp."""
        url = f"https://twitter.com/i/status/{tweet_id}"
        output_template = str(self.videos_dir / f"video_{index:03d}_%(id)s.%(ext)s")

        logger.info(f"[{index}] Downloading tweet {tweet_id}...")

        try:
            # yt-dlp command
            cmd = [
                "yt-dlp",
                "--quiet",
                "--no-warnings",
                "-f",
                "best",  # Best quality
                "-o",
                output_template,
                "--write-info-json",  # Save metadata
                "--no-playlist",
                url,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                # Find downloaded file
                video_files = list(
                    self.videos_dir.glob(f"video_{index:03d}_*.mp4")
                ) + list(self.videos_dir.glob(f"video_{index:03d}_*.webm"))

                if video_files:
                    video_file = video_files[0]
                    logger.info(f"  ✓ Downloaded: {video_file.name}")

                    # Read metadata if available
                    info_file = video_file.with_suffix(".info.json")
                    metadata = {
                        "index": index,
                        "tweet_id": tweet_id,
                        "url": url,
                        "filename": video_file.name,
                        "downloaded": True,
                        "error": None,
                    }

                    if info_file.exists():
                        try:
                            with open(info_file, "r") as f:
                                info = json.load(f)
                                metadata["duration"] = info.get("duration", 0)
                                metadata["title"] = info.get("title", "")
                                metadata["uploader"] = info.get("uploader", "")
                        except:
                            pass

                    self.metadata.append(metadata)
                    return True
                else:
                    logger.warning(f"  ✗ Video file not found after download")
                    self.metadata.append(
                        {
                            "index": index,
                            "tweet_id": tweet_id,
                            "url": url,
                            "downloaded": False,
                            "error": "Video file not found",
                        }
                    )
                    return False
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                logger.warning(f"  ✗ Failed: {error_msg[:100]}")
                self.metadata.append(
                    {
                        "index": index,
                        "tweet_id": tweet_id,
                        "url": url,
                        "downloaded": False,
                        "error": error_msg[:200],
                    }
                )
                return False

        except subprocess.TimeoutExpired:
            logger.warning(f"  ✗ Timeout downloading tweet {tweet_id}")
            self.metadata.append(
                {
                    "index": index,
                    "tweet_id": tweet_id,
                    "url": url,
                    "downloaded": False,
                    "error": "Download timeout",
                }
            )
            return False
        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            self.metadata.append(
                {
                    "index": index,
                    "tweet_id": tweet_id,
                    "url": url,
                    "downloaded": False,
                    "error": str(e),
                }
            )
            return False

    def save_metadata(self):
        """Save download metadata."""
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)
        logger.info(f"\nMetadata saved to: {self.metadata_file}")

    def run(self, limit=30):
        """Main execution."""
        logger.info("=" * 70)
        logger.info(f"VIDEO DOWNLOADER - Downloading {limit} Sample Videos")
        logger.info("=" * 70)

        # Check yt-dlp
        if not self.check_ytdlp():
            return None

        # Load video notes
        logger.info("\nLoading video notes...")
        df = self.load_video_notes(limit=limit)

        if df is None or df.empty:
            logger.error("No video notes to process")
            return None

        # Extract tweet IDs
        tweet_ids = df["tweetId"].tolist()
        logger.info(f"\nProcessing {len(tweet_ids)} tweets...")

        # Download videos
        success_count = 0
        fail_count = 0

        for i, tweet_id in enumerate(tweet_ids, 1):
            if self.download_video(tweet_id, i):
                success_count += 1
            else:
                fail_count += 1

            # Brief pause between downloads
            if i < len(tweet_ids):
                time.sleep(1)

        # Save metadata
        self.save_metadata()

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("DOWNLOAD COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total attempted: {len(tweet_ids)}")
        logger.info(
            f"Successful: {success_count} ({success_count/len(tweet_ids)*100:.1f}%)"
        )
        logger.info(f"Failed: {fail_count} ({fail_count/len(tweet_ids)*100:.1f}%)")
        logger.info(f"\nVideos saved to: {self.videos_dir}")
        logger.info(f"Metadata: {self.metadata_file}")

        # List downloaded files
        video_files = list(self.videos_dir.glob("video_*.mp4")) + list(
            self.videos_dir.glob("video_*.webm")
        )

        if video_files:
            logger.info(f"\nDownloaded files ({len(video_files)}):")
            for vf in sorted(video_files)[:10]:
                size_mb = vf.stat().st_size / (1024 * 1024)
                logger.info(f"  - {vf.name} ({size_mb:.1f} MB)")
            if len(video_files) > 10:
                logger.info(f"  ... and {len(video_files) - 10} more")

        return self.metadata


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download sample videos from likely video notes"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Number of videos to download (default: 30)",
    )
    args = parser.parse_args()

    downloader = VideoDownloader(data_dir="data")
    result = downloader.run(limit=args.limit)

    if result is not None:
        print(f"\n✓ Video download completed!")
        print(f"✓ Check data/videos/ directory")
    else:
        print("\n✗ Failed to download videos")


if __name__ == "__main__":
    main()

"""
Download Sample Videos from Twitter
Downloads videos from media_metadata table in database using yt-dlp.
Automatically skips already-downloaded videos unless --force is used.
"""

import pandas as pd
from pathlib import Path
import logging
import subprocess
import json
import time
import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import get_session, MediaMetadata, Tweet

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VideoDownloader:
    def __init__(
        self, data_dir="data", force=False, random_sample=False, random_seed=42
    ):
        self.data_dir = Path(data_dir)
        self.filtered_dir = self.data_dir / "filtered"

        # Get video download path from environment variable or use default
        video_path_env = os.getenv("VIDEO_DOWNLOAD_PATH")
        if video_path_env:
            self.videos_dir = Path(video_path_env)
            logger.info(
                f"Using custom video download path from .env: {self.videos_dir}"
            )
        else:
            self.videos_dir = self.data_dir / "videos"
            logger.info(f"Using default video download path: {self.videos_dir}")

        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.force = force  # Force re-download even if already downloaded
        self.random_sample = random_sample  # Enable random sampling
        self.random_seed = random_seed  # Seed for reproducibility

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

    def load_video_notes(self, session, limit=None):
        """Load video metadata from database.

        Args:
            session: Database session
            limit: Number of videos to load

        Returns:
            List of MediaMetadata objects to download
        """
        try:
            # Query videos from media_metadata table
            query = session.query(MediaMetadata).filter(
                MediaMetadata.media_type == "video"
            )

            # Filter out already-downloaded videos (unless force mode)
            if not self.force:
                # Check if local_path exists and file actually exists
                videos = query.all()
                videos_to_download = []

                for video in videos:
                    if video.local_path:
                        # Check if file actually exists
                        video_path = Path(video.local_path)
                        if video_path.exists():
                            continue  # Skip - already downloaded
                    videos_to_download.append(video)

                logger.info(f"Found {len(videos)} videos in database")
                logger.info(
                    f"Already downloaded: {len(videos) - len(videos_to_download)}"
                )
                logger.info(f"To download: {len(videos_to_download)}")
            else:
                videos_to_download = query.all()
                logger.info(
                    f"Force mode: Re-downloading all {len(videos_to_download)} videos"
                )

            # Apply random sampling if enabled
            if self.random_sample and len(videos_to_download) > 0:
                import random

                random.seed(self.random_seed)
                random.shuffle(videos_to_download)
                logger.info(f"Random sampling enabled (seed: {self.random_seed})")

            if limit and len(videos_to_download) > limit:
                videos_to_download = videos_to_download[:limit]
                logger.info(f"Limited to {limit} videos")

            return videos_to_download

        except Exception as e:
            logger.error(f"Failed to load video metadata from database: {e}")
            return []

    def download_video(self, media_metadata, index, session):
        """Download a single video using yt-dlp and update database.

        Args:
            media_metadata: MediaMetadata object from database
            index: Download index for naming
            session: Database session for updating local_path
        """
        tweet_id = media_metadata.tweet_id
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

                    # Update database with local_path
                    try:
                        media_metadata.local_path = str(video_file.absolute())
                        session.commit()
                    except Exception as e:
                        logger.warning(f"  Failed to update database: {e}")
                        session.rollback()

                    # Read metadata if available
                    info_file = video_file.with_suffix(".info.json")
                    metadata = {
                        "index": index,
                        "tweet_id": tweet_id,
                        "url": url,
                        "filename": video_file.name,
                        "local_path": str(video_file.absolute()),
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
        logger.info(f"VIDEO DOWNLOADER - Downloading up to {limit} Videos")
        logger.info("=" * 70)

        # Check yt-dlp
        if not self.check_ytdlp():
            return None

        with get_session() as session:
            # Load video metadata from database
            logger.info("\nQuerying videos from database...")
            videos_to_download = self.load_video_notes(session, limit=limit)

            if not videos_to_download:
                logger.info("No videos to download!")
                return []

            logger.info(f"\nProcessing {len(videos_to_download)} videos...")

            # Download videos
            success_count = 0
            fail_count = 0

            for i, media_metadata in enumerate(videos_to_download, 1):
                if self.download_video(media_metadata, i, session):
                    success_count += 1
                else:
                    fail_count += 1

                # Brief pause between downloads
                if i < len(videos_to_download):
                    time.sleep(1)

            # Save metadata
            self.save_metadata()

            # Summary
            logger.info("\n" + "=" * 70)
            logger.info("DOWNLOAD COMPLETE")
            logger.info("=" * 70)
            logger.info(f"Total attempted: {len(videos_to_download)}")
            logger.info(
                f"Successful: {success_count} ({success_count/len(videos_to_download)*100:.1f}%)"
            )
            logger.info(
                f"Failed: {fail_count} ({fail_count/len(videos_to_download)*100:.1f}%)"
            )
            logger.info(f"\nVideos saved to: {self.videos_dir}")
            logger.info(f"Metadata: {self.metadata_file}")
            logger.info("Database updated with local_path for downloaded videos")

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
        description="Download videos from database (media_metadata table)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Number of videos to download (default: 30)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download all videos, even if already downloaded",
    )
    parser.add_argument(
        "--random",
        action="store_true",
        help="Enable random sampling for diverse video selection",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42)",
    )
    args = parser.parse_args()

    downloader = VideoDownloader(
        data_dir="data",
        force=args.force,
        random_sample=args.random,
        random_seed=args.seed,
    )
    result = downloader.run(limit=args.limit)

    if result is not None:
        print(f"\n✓ Video download completed!")
        print(f"✓ Check data/videos/ directory")
        print(f"✓ Database updated with local file paths")
    else:
        print("\n✗ Failed to download videos")


if __name__ == "__main__":
    main()

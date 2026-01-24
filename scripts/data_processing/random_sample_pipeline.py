"""
Random Sample Pipeline - Quick Dataset Creation

Randomly samples tweets with CURRENTLY_RATED_HELPFUL notes, downloads videos,
and creates evaluation dataset. Maximum randomness for diverse sampling.

Usage:
    python scripts/data_processing/random_sample_pipeline.py --limit 30
    python scripts/data_processing/random_sample_pipeline.py --limit 50 --seed 42
    python scripts/data_processing/random_sample_pipeline.py --limit 100 --force
"""

import sys
from pathlib import Path
import logging
import argparse
import subprocess
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import get_session, Note, Tweet, MediaMetadata
from sqlalchemy import func, text

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RandomSamplePipeline:
    """Pipeline for randomly sampling notes by status, downloading videos, and creating dataset."""

    def __init__(
        self, limit=30, seed=None, force=False, status="CURRENTLY_RATED_HELPFUL"
    ):
        self.limit = limit
        self.seed = (
            seed if seed is not None else int(datetime.now().timestamp() * 1000) % 2**32
        )
        self.force = force
        self.status = status  # Note status filter
        logger.info(f"Random seed: {self.seed}")
        logger.info(f"Note status filter: {self.status}")

    def sample_notes_by_status(self):
        """
        Randomly sample tweets with notes matching the specified status.
        Uses database-level random sampling for maximum randomness.

        Returns:
            List of tweet_ids to process
        """
        logger.info("\n" + "=" * 70)
        logger.info(f"Step 1: Sampling Random Tweets with {self.status} Notes")
        logger.info("=" * 70)

        with get_session() as session:
            # Set random seed for this session (PostgreSQL-specific)
            session.execute(text(f"SELECT setseed({self.seed / 2**32})"))

            # Query tweets with specified status
            # Use random() for database-level randomization
            query = (
                session.query(Note.tweet_id)
                .filter(Note.current_status == self.status)
                .order_by(func.random())
                .limit(
                    self.limit * 1
                )  # Sample 4x: ~50% are original, ~80% are English = ~40% pass
            )

            tweet_ids = [row.tweet_id for row in query.all()]

            logger.info(f"✓ Sampled {len(tweet_ids)} tweets with {self.status} notes")
            logger.info(f"  Filter: current_status = {self.status}")
            logger.info(f"  Seed: {self.seed}")

            return tweet_ids

    def fetch_api_data_for_tweets(self, tweet_ids):
        """
        Fetch Twitter API data for sampled tweets.
        Step 1.5: Get API data before video identification.

        Args:
            tweet_ids: List of tweet IDs to fetch API data for

        Returns:
            True if successful, False otherwise
        """
        logger.info("\n" + "=" * 70)
        logger.info("Step 1.5: Fetching Twitter API Data")
        logger.info("=" * 70)

        from scripts.services.twitter_service import TwitterService

        twitter = TwitterService()

        if not twitter.is_available():
            logger.error("Twitter API not available! Cannot proceed.")
            logger.error("Set TWITTER_BEARER_TOKEN in .env file")
            return False

        logger.info(f"Fetching API data for {len(tweet_ids)} tweets...")
        twitter.fetch_tweets([str(tid) for tid in tweet_ids], save_to_db=True)

        logger.info(f"✓ API data fetched and saved to database")
        return True

    def filter_original_english_tweets(self, tweet_ids):
        """
        Filter for original (non-RT/reply) English tweets.
        Step 2: Apply filters BEFORE identifying videos.

        Args:
            tweet_ids: List of tweet IDs to filter

        Returns:
            List of filtered tweet IDs
        """
        logger.info("\n" + "=" * 70)
        logger.info("Step 2: Filtering for Original English Tweets")
        logger.info("=" * 70)

        from database import get_session, Tweet
        from scripts.data_processing.create_dataset import DatasetCreator

        with get_session() as session:
            tweets = session.query(Tweet).filter(Tweet.tweet_id.in_(tweet_ids)).all()

            original_count = 0
            english_count = 0
            filtered_ids = []

            for tweet in tweets:
                if not DatasetCreator.is_original_tweet(tweet):
                    continue
                original_count += 1

                if not DatasetCreator.is_english_tweet(tweet):
                    continue
                english_count += 1

                filtered_ids.append(tweet.tweet_id)

            logger.info(f"Total tweets checked: {len(tweets)}")
            logger.info(f"  ✓ Original (not RT/reply): {original_count}")
            logger.info(f"  ✓ English: {english_count}")
            logger.info(f"  Final filtered: {len(filtered_ids)}")
            logger.info(f"  Filtered out: {len(tweets) - len(filtered_ids)}")

            return filtered_ids

    def identify_video_tweets(self, tweet_ids):
        """
        Check which tweets actually contain videos using yt-dlp metadata.

        Args:
            tweet_ids: List of tweet IDs to check

        Returns:
            Number of video tweets identified
        """
        logger.info("\n" + "=" * 70)
        logger.info("Step 3: Identifying Video Tweets")
        logger.info("=" * 70)

        # Use the existing identify_video_notes script
        # Create a temporary file with tweet IDs
        temp_file = Path("data/temp_sample_tweets.txt")
        temp_file.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_file, "w") as f:
            for tweet_id in tweet_ids:
                f.write(f"{tweet_id}\n")

        logger.info(f"Checking {len(tweet_ids)} tweets for video content...")

        # Call identify_video_notes.py with force flag if needed
        cmd = [
            sys.executable,
            "scripts/data_processing/identify_video_notes.py",
            "--tweet-ids-file",
            str(temp_file),
        ]

        if self.force:
            cmd.append("--force")

        try:
            subprocess.run(cmd, check=True)

            # Count how many videos we found
            with get_session() as session:
                video_count = (
                    session.query(MediaMetadata)
                    .filter(
                        MediaMetadata.tweet_id.in_(tweet_ids),
                        MediaMetadata.media_type == "video",
                    )
                    .count()
                )

                logger.info(f"✓ Found {video_count} video tweets")
                return video_count

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to identify videos: {e}")
            return 0
        finally:
            # Clean up temp file
            if temp_file.exists():
                temp_file.unlink()

    def download_videos(self, tweet_ids):
        """
        Download videos using the existing download_videos script.

        Args:
            tweet_ids: List of tweet IDs to download videos from

        Returns:
            True if successful, False otherwise
        """
        logger.info("\n" + "=" * 70)
        logger.info("Step 4: Downloading Videos")
        logger.info("=" * 70)

        # Save tweet_ids to temporary file for download_videos.py
        temp_file = Path("data/temp_download_tweets.txt")
        temp_file.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_file, "w") as f:
            for tweet_id in tweet_ids:
                f.write(f"{tweet_id}\n")

        logger.info(f"Downloading videos from {len(tweet_ids)} pre-filtered tweets")

        cmd = [
            sys.executable,
            "scripts/data_processing/download_videos.py",
            "--limit",
            str(self.limit),
            "--random",
            "--seed",
            str(self.seed),
            "--tweet-ids-file",
            str(temp_file),
        ]

        if self.force:
            cmd.append("--force")

        try:
            subprocess.run(cmd, check=True)
            logger.info(f"✓ Video download completed")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download videos: {e}")
            return False
        finally:
            # Clean up temp file
            if temp_file.exists():
                temp_file.unlink()

    def create_dataset(self):
        """
        Create evaluation dataset using the existing create_dataset script.
        Passes the status filter to only include matching notes.

        Returns:
            True if successful, False otherwise
        """
        logger.info("\n" + "=" * 70)
        logger.info("Step 5: Creating Evaluation Dataset")
        logger.info("=" * 70)

        cmd = [
            sys.executable,
            "scripts/data_processing/create_dataset.py",
            "--note-status",
            self.status,
        ]

        if self.force:
            cmd.append("--force-api-fetch")

        try:
            subprocess.run(cmd, check=True)
            logger.info(f"✓ Dataset created successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create dataset: {e}")
            return False

    def run(self):
        """
        Run the complete random sample pipeline.
        """
        logger.info("\n" + "=" * 70)
        logger.info("RANDOM SAMPLE PIPELINE")
        logger.info("=" * 70)
        logger.info(f"Target: {self.limit} videos from {self.status} notes")
        logger.info(f"Random seed: {self.seed}")
        logger.info(f"Force mode: {self.force}")
        logger.info("=" * 70)

        start_time = datetime.now()

        # Step 1: Sample notes by status
        tweet_ids = self.sample_notes_by_status()
        if not tweet_ids:
            logger.error(f"No notes with status {self.status} found!")
            return False

        # Step 1.5: Fetch API data (NEW)
        if not self.fetch_api_data_for_tweets(tweet_ids):
            return False

        # Step 2: Filter for original English tweets (NEW)
        filtered_tweet_ids = self.filter_original_english_tweets(tweet_ids)
        if not filtered_tweet_ids:
            logger.error("No tweets passed original/English filters!")
            return False

        # Adjust limit based on filtered results
        adjusted_limit = min(self.limit, len(filtered_tweet_ids))
        if adjusted_limit < self.limit:
            logger.info(
                f"Adjusted video download limit: {adjusted_limit} (fewer tweets passed filters)"
            )

        # Step 3: Identify video tweets (use filtered IDs)
        video_count = self.identify_video_tweets(filtered_tweet_ids)
        if video_count == 0:
            logger.error("No video tweets found!")
            return False

        # Step 4: Download videos (use filtered IDs)
        if not self.download_videos(filtered_tweet_ids):
            logger.error("Video download failed!")
            return False

        # Step 5: Create dataset
        if not self.create_dataset():
            logger.error("Dataset creation failed!")
            return False

        # Summary
        elapsed = datetime.now() - start_time
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE COMPLETE!")
        logger.info("=" * 70)
        logger.info(f"✓ Successfully created dataset")
        logger.info(f"✓ From {self.status} notes only")
        logger.info(f"✓ Original English tweets only")
        logger.info(f"✓ Random seed: {self.seed}")
        logger.info(f"✓ Time elapsed: {elapsed}")
        logger.info(f"\nDataset location: data/evaluation/latest/dataset.json")
        logger.info("=" * 70)

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Random sample pipeline: Sample notes by status, download videos, create dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Number of videos to download (default: 30)",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (default: timestamp-based)",
    )

    parser.add_argument(
        "--force", action="store_true", help="Force re-processing even if data exists"
    )

    parser.add_argument(
        "--status",
        type=str,
        default="CURRENTLY_RATED_HELPFUL",
        help="Note status to filter by (default: CURRENTLY_RATED_HELPFUL). Other options: CURRENTLY_RATED_NOT_HELPFUL, NEEDS_MORE_RATINGS, etc.",
    )

    args = parser.parse_args()

    pipeline = RandomSamplePipeline(
        limit=args.limit, seed=args.seed, force=args.force, status=args.status
    )

    success = pipeline.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

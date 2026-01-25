"""
Random Sample Pipeline - Quick Dataset Creation

Randomly samples tweets with notes by status, identifies which have videos,
downloads videos, then fetches API data and creates evaluation dataset.

NEW WORKFLOW (to respect API rate limits):
1. Sample tweets WITHOUT existing API data (need fresh ones)
2. Check metadata to identify which have videos (resample until target met)
3. Download the videos
4. Call API for those tweets
5. Create dataset (original/English filtering happens here, some may be filtered out)

Usage:
    python scripts/data_processing/random_sample_pipeline.py --limit 100
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
        self.video_tweet_ids = []  # Store the final video tweet IDs for dataset creation
        logger.info(f"Random seed: {self.seed}")
        logger.info(f"Note status filter: {self.status}")

    def sample_notes_by_status(self, exclude_existing=True):
        """
        Randomly sample tweets with notes matching the specified status.
        Uses database-level random sampling for maximum randomness.

        Args:
            exclude_existing: If True, only sample tweets WITHOUT api_data

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
                .join(Tweet, Tweet.tweet_id == Note.tweet_id)
                .filter(Note.current_status == self.status)
            )

            # Exclude tweets that already have API data (we want fresh ones)
            if exclude_existing:
                query = query.filter(Tweet.raw_api_data.is_(None))
                logger.info("Filtering: Only tweets WITHOUT existing API data")

            query = query.order_by(func.random()).limit(self.limit * 10)  # Sample extra

            tweet_ids = [row.tweet_id for row in query.all()]

            logger.info(f"✓ Sampled {len(tweet_ids)} candidate tweets")
            logger.info(f"  Filter: current_status = {self.status}")
            logger.info(f"  Seed: {self.seed}")

            return tweet_ids

    def identify_video_tweets(self, tweet_ids):
        """
        Check which tweets actually contain videos using yt-dlp metadata.
        This checks Twitter directly to see if videos exist.

        Args:
            tweet_ids: List of tweet IDs to check

        Returns:
            List of tweet IDs that have videos
        """
        logger.info("\n" + "=" * 70)
        logger.info("Step 2: Identifying Video Tweets (Metadata Check)")
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

            # Get list of tweets that have videos
            with get_session() as session:
                video_tweets = (
                    session.query(MediaMetadata.tweet_id)
                    .filter(
                        MediaMetadata.tweet_id.in_(tweet_ids),
                        MediaMetadata.media_type == "video",
                    )
                    .distinct()
                    .all()
                )

                video_tweet_ids = [row.tweet_id for row in video_tweets]
                logger.info(f"✓ Found {len(video_tweet_ids)} tweets with videos")
                return video_tweet_ids

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to identify videos: {e}")
            return []
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
        logger.info("Step 3: Downloading Videos")
        logger.info("=" * 70)

        # Save tweet_ids to temporary file for download_videos.py
        temp_file = Path("data/temp_download_tweets.txt")
        temp_file.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_file, "w") as f:
            for tweet_id in tweet_ids:
                f.write(f"{tweet_id}\n")

        logger.info(f"Downloading videos from {len(tweet_ids)} video tweets")

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

    def fetch_api_data_for_tweets(self, tweet_ids):
        """
        Fetch Twitter API data for tweets with downloaded videos.
        Step 4: Get API data AFTER video download.

        Args:
            tweet_ids: List of tweet IDs to fetch API data for

        Returns:
            True if successful, False otherwise
        """
        logger.info("\n" + "=" * 70)
        logger.info("Step 4: Fetching Twitter API Data")
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

    def create_dataset(self):
        """
        Create evaluation dataset using the existing create_dataset script.
        Now uses only the video tweet IDs from this pipeline run.
        Passes the status filter to only include matching notes.

        Returns:
            True if successful, False otherwise
        """
        logger.info("\n" + "=" * 70)
        logger.info("Step 5: Creating Evaluation Dataset")
        logger.info("=" * 70)

        # Create a temporary file with the video tweet IDs
        temp_ids_file = Path("data/temp_pipeline_tweet_ids.txt")
        temp_ids_file.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_ids_file, "w") as f:
            for tweet_id in self.video_tweet_ids:
                f.write(f"{tweet_id}\n")

        logger.info(f"Creating dataset with {len(self.video_tweet_ids)} video tweets")

        cmd = [
            sys.executable,
            "scripts/data_processing/create_dataset.py",
            "--note-status",
            self.status,
            "--tweet-ids-file",
            str(temp_ids_file),
        ]

        if self.force:
            cmd.append("--force-api-fetch")

        try:
            subprocess.run(cmd, check=True)
            logger.info(f"✓ Dataset created successfully")
            
            # Clean up temp file
            temp_ids_file.unlink(missing_ok=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create dataset: {e}")
            # Clean up temp file even on error
            temp_ids_file.unlink(missing_ok=True)
            return False

    def run(self):
        """
        Run the complete random sample pipeline with NEW workflow:
        1. Sample tweets WITHOUT api_data
        2. Identify which have videos (metadata check), resample if needed
        3. Download videos
        4. Call API for those tweets
        5. Create dataset (filtering is fine here)
        """
        logger.info("\n" + "=" * 70)
        logger.info("RANDOM SAMPLE PIPELINE")
        logger.info("=" * 70)
        logger.info(f"Target: {self.limit} video tweets from {self.status} notes")
        logger.info(f"Random seed: {self.seed}")
        logger.info(f"Force mode: {self.force}")
        logger.info("=" * 70)

        start_time = datetime.now()

        # Step 1: Sample tweets WITHOUT existing API data
        video_tweet_ids = []
        attempts = 0
        max_attempts = 10

        while len(video_tweet_ids) < self.limit and attempts < max_attempts:
            attempts += 1
            logger.info(
                f"\n[Sampling Attempt {attempts}] Need {self.limit - len(video_tweet_ids)} more video tweets"
            )

            # Sample candidate tweets
            candidate_tweet_ids = self.sample_notes_by_status(exclude_existing=True)
            if not candidate_tweet_ids:
                logger.error(f"No more tweets to sample (all have API data)!")
                break

            # Step 2: Identify which have videos
            new_video_tweet_ids = self.identify_video_tweets(candidate_tweet_ids)
            if not new_video_tweet_ids:
                logger.warning("No video tweets found in this batch, resampling...")
                continue

            # Add to our collection (avoid duplicates)
            for tweet_id in new_video_tweet_ids:
                if tweet_id not in video_tweet_ids:
                    video_tweet_ids.append(tweet_id)
                    if len(video_tweet_ids) >= self.limit:
                        break

            logger.info(
                f"Progress: {len(video_tweet_ids)}/{self.limit} video tweets collected"
            )

        # Trim to exact limit
        video_tweet_ids = video_tweet_ids[: self.limit]

        if not video_tweet_ids:
            logger.error("Failed to find any video tweets!")
            return False

        # Store for use in create_dataset()
        self.video_tweet_ids = video_tweet_ids

        logger.info(
            f"\n✓ Collected {len(video_tweet_ids)} video tweets after {attempts} attempts"
        )

        # Step 3: Download videos
        if not self.download_videos(video_tweet_ids):
            logger.error("Video download failed!")
            return False

        # Step 4: Fetch API data for these tweets
        if not self.fetch_api_data_for_tweets(video_tweet_ids):
            logger.error("API fetch failed!")
            return False

        # Step 5: Create dataset (filtering happens here)
        if not self.create_dataset():
            logger.error("Dataset creation failed!")
            return False

        # Summary
        elapsed = datetime.now() - start_time
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE COMPLETE!")
        logger.info("=" * 70)
        logger.info(f"✓ Successfully created dataset")
        logger.info(f"✓ Started with {len(video_tweet_ids)} video tweets")
        logger.info(f"✓ From {self.status} notes only")
        logger.info(f"✓ Random seed: {self.seed}")
        logger.info(f"✓ Time elapsed: {elapsed}")
        logger.info(f"\nDataset location: data/evaluation/latest/dataset.json")
        logger.info(
            "Note: Final dataset may have fewer tweets due to original/English filtering"
        )
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

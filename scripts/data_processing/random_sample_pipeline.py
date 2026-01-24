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
    
    def __init__(self, limit=30, seed=None, force=False, status="CURRENTLY_RATED_HELPFUL"):
        self.limit = limit
        self.seed = seed if seed is not None else int(datetime.now().timestamp() * 1000) % 2**32
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
        logger.info("\n" + "="*70)
        logger.info(f"Step 1: Sampling Random Tweets with {self.status} Notes")
        logger.info("="*70)
        
        with get_session() as session:
            # Set random seed for this session (PostgreSQL-specific)
            session.execute(text(f"SELECT setseed({self.seed / 2**32})"))
            
            # Query tweets with specified status
            # Use random() for database-level randomization
            query = (
                session.query(Note.tweet_id)
                .filter(Note.current_status == self.status)
                .order_by(func.random())
                .limit(self.limit * 10)  # Sample extra to account for videos that fail
            )
            
            tweet_ids = [row.tweet_id for row in query.all()]
            
            logger.info(f"✓ Sampled {len(tweet_ids)} tweets with {self.status} notes")
            logger.info(f"  Filter: current_status = {self.status}")
            logger.info(f"  Seed: {self.seed}")
            
            return tweet_ids
    
    def identify_video_tweets(self, tweet_ids):
        """
        Check which tweets actually contain videos using yt-dlp metadata.
        
        Args:
            tweet_ids: List of tweet IDs to check
            
        Returns:
            Number of video tweets identified
        """
        logger.info("\n" + "="*70)
        logger.info("Step 2: Identifying Video Tweets")
        logger.info("="*70)
        
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
            "--tweet-ids-file", str(temp_file)
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
                        MediaMetadata.media_type == "video"
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
    
    def download_videos(self):
        """
        Download videos using the existing download_videos script.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("\n" + "="*70)
        logger.info("Step 3: Downloading Videos")
        logger.info("="*70)
        
        cmd = [
            sys.executable,
            "scripts/data_processing/download_videos.py",
            "--limit", str(self.limit),
            "--random",
            "--seed", str(self.seed)
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
    
    def create_dataset(self):
        """
        Create evaluation dataset using the existing create_dataset script.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("\n" + "="*70)
        logger.info("Step 4: Creating Evaluation Dataset")
        logger.info("="*70)
        
        cmd = [
            sys.executable,
            "scripts/data_processing/create_dataset.py"
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
        logger.info("\n" + "="*70)
        logger.info("RANDOM SAMPLE PIPELINE")
        logger.info("="*70)
        logger.info(f"Target: {self.limit} videos from {self.status} notes")
        logger.info(f"Random seed: {self.seed}")
        logger.info(f"Force mode: {self.force}")
        logger.info("="*70)
        
        start_time = datetime.now()
        
        # Step 1: Sample notes by status
        tweet_ids = self.sample_notes_by_status()
        if not tweet_ids:
            logger.error(f"No notes with status {self.status} found!")
            return False
        
        # Step 2: Identify video tweets
        video_count = self.identify_video_tweets(tweet_ids)
        if video_count == 0:
            logger.error("No video tweets found!")
            return False
        
        # Step 3: Download videos
        if not self.download_videos():
            logger.error("Video download failed!")
            return False
        
        # Step 4: Create dataset
        if not self.create_dataset():
            logger.error("Dataset creation failed!")
            return False
        
        # Summary
        elapsed = datetime.now() - start_time
        logger.info("\n" + "="*70)
        logger.info("PIPELINE COMPLETE!")
        logger.info("="*70)
        logger.info(f"✓ Successfully created dataset with {self.limit} videos")
        logger.info(f"✓ From {self.status} notes only")
        logger.info(f"✓ Random seed: {self.seed}")
        logger.info(f"✓ Time elapsed: {elapsed}")
        logger.info(f"\nDataset location: data/evaluation/dataset.json")
        logger.info("="*70)
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Random sample pipeline: Sample notes by status, download videos, create dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Number of videos to download (default: 30)"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (default: timestamp-based)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-processing even if data exists"
    )
    
    parser.add_argument(
        "--status",
        type=str,
        default="CURRENTLY_RATED_HELPFUL",
        help="Note status to filter by (default: CURRENTLY_RATED_HELPFUL). Other options: CURRENTLY_RATED_NOT_HELPFUL, NEEDS_MORE_RATINGS, etc."
    )
    
    args = parser.parse_args()
    
    pipeline = RandomSamplePipeline(
        limit=args.limit,
        seed=args.seed,
        force=args.force,
        status=args.status
    )
    
    success = pipeline.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Re-download Videos for Specific Tweet IDs

This script downloads videos only for tweets that previously had videos.
Uses the tweet_ids saved from reset_and_redownload.py.
"""

import json
import logging
from pathlib import Path
import subprocess
import time
import sys

sys.path.insert(0, str(Path(__file__).parent))

from database import get_session, MediaMetadata
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SpecificTweetDownloader:
    """Download videos for specific tweet IDs."""
    
    def __init__(self, tweet_ids_file="tweets_to_redownload.json", videos_dir="data/videos"):
        self.tweet_ids_file = tweet_ids_file
        self.videos_dir = Path(videos_dir)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            "total_tweets": 0,
            "already_downloaded": 0,
            "downloaded": 0,
            "failed": 0,
            "db_updated": 0
        }
    
    def load_tweet_ids(self):
        """Load tweet IDs from saved file."""
        logger.info(f"Loading tweet IDs from {self.tweet_ids_file}...")
        
        with open(self.tweet_ids_file) as f:
            data = json.load(f)
        
        tweet_ids = data["tweet_ids"]
        self.stats["total_tweets"] = len(tweet_ids)
        
        logger.info(f"Loaded {len(tweet_ids)} tweet IDs")
        logger.info(f"Original save date: {data.get('timestamp', 'unknown')}")
        
        return tweet_ids
    
    def check_existing(self, tweet_id):
        """Check if video already exists for this tweet."""
        # Check for file in new format
        video_file = self.videos_dir / f"{tweet_id}_1.mp4"
        if video_file.exists():
            return str(video_file.absolute())
        
        # Check for webm
        video_file = self.videos_dir / f"{tweet_id}_1.webm"
        if video_file.exists():
            return str(video_file.absolute())
        
        return None
    
    def download_video(self, tweet_id, index):
        """Download a single video using yt-dlp."""
        url = f"https://twitter.com/i/status/{tweet_id}"
        
        # Use new naming convention
        output_template = str(self.videos_dir / f"{tweet_id}_1.%(ext)s")
        
        logger.info(f"[{index}] Downloading tweet {tweet_id}...")
        
        try:
            cmd = [
                "yt-dlp",
                "--quiet",
                "--no-warnings",
                "-f", "best",
                "-o", output_template,
                "--write-info-json",
                "--no-playlist",
                url,
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # Find downloaded file
                video_files = list(self.videos_dir.glob(f"{tweet_id}_1.mp4")) + \
                             list(self.videos_dir.glob(f"{tweet_id}_1.webm"))
                
                if video_files:
                    video_file = video_files[0]
                    logger.info(f"  ✓ Downloaded: {video_file.name}")
                    self.stats["downloaded"] += 1
                    return str(video_file.absolute())
                else:
                    logger.warning(f"  ✗ Video file not found after download")
                    self.stats["failed"] += 1
                    return None
            else:
                logger.warning(f"  ✗ Download failed: {result.stderr[:100]}")
                self.stats["failed"] += 1
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"  ✗ Download timeout")
            self.stats["failed"] += 1
            return None
        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            self.stats["failed"] += 1
            return None
    
    def update_database(self, tweet_id, local_path):
        """Update database with new local_path."""
        with get_session() as session:
            try:
                sql = text("""
                    UPDATE media_metadata
                    SET local_path = :local_path
                    WHERE tweet_id = :tweet_id
                    AND media_type = 'video'
                """)
                
                result = session.execute(sql, {
                    'local_path': local_path,
                    'tweet_id': int(tweet_id)
                })
                
                session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"  ✓ Updated database for tweet {tweet_id}")
                    self.stats["db_updated"] += 1
                    return True
                else:
                    logger.warning(f"  ⚠ No database record found for tweet {tweet_id}")
                    return False
                    
            except Exception as e:
                logger.error(f"  ✗ Database update failed: {e}")
                session.rollback()
                return False
    
    def process_tweets(self, tweet_ids, limit=None):
        """Process list of tweet IDs."""
        if limit:
            tweet_ids = tweet_ids[:limit]
            logger.info(f"Limited to {limit} tweets")
        
        logger.info(f"\nProcessing {len(tweet_ids)} tweets...")
        logger.info("="*60)
        
        for idx, tweet_id in enumerate(tweet_ids, 1):
            # Check if already exists
            existing_path = self.check_existing(tweet_id)
            if existing_path:
                logger.info(f"[{idx}/{len(tweet_ids)}] Tweet {tweet_id}: Already exists")
                self.stats["already_downloaded"] += 1
                # Still update database in case it's NULL
                self.update_database(tweet_id, existing_path)
                continue
            
            # Download
            local_path = self.download_video(tweet_id, f"{idx}/{len(tweet_ids)}")
            
            if local_path:
                # Update database
                self.update_database(tweet_id, local_path)
            
            # Rate limiting
            time.sleep(1)
        
        logger.info("="*60)
    
    def print_summary(self):
        """Print summary of operations."""
        logger.info("\n" + "="*60)
        logger.info("SUMMARY")
        logger.info("="*60)
        logger.info(f"Total tweets to process: {self.stats['total_tweets']}")
        logger.info(f"Already downloaded: {self.stats['already_downloaded']}")
        logger.info(f"Newly downloaded: {self.stats['downloaded']}")
        logger.info(f"Failed downloads: {self.stats['failed']}")
        logger.info(f"Database updated: {self.stats['db_updated']}")
        logger.info("="*60)
        
        success_rate = 0
        if self.stats['total_tweets'] > 0:
            successful = self.stats['already_downloaded'] + self.stats['downloaded']
            success_rate = (successful / self.stats['total_tweets']) * 100
        
        logger.info(f"\n✓ Success rate: {success_rate:.1f}%")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Re-download videos for specific tweet IDs"
    )
    parser.add_argument(
        "--tweet-ids-file",
        default="tweets_to_redownload.json",
        help="JSON file with tweet IDs (default: tweets_to_redownload.json)"
    )
    parser.add_argument(
        "--videos-dir",
        default="data/videos",
        help="Videos directory (default: data/videos)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of videos to download"
    )
    
    args = parser.parse_args()
    
    # Check if tweet IDs file exists
    if not Path(args.tweet_ids_file).exists():
        logger.error(f"Tweet IDs file not found: {args.tweet_ids_file}")
        logger.error("Run reset_and_redownload.py first to generate the file")
        sys.exit(1)
    
    # Create downloader
    downloader = SpecificTweetDownloader(
        tweet_ids_file=args.tweet_ids_file,
        videos_dir=args.videos_dir
    )
    
    # Load tweet IDs
    tweet_ids = downloader.load_tweet_ids()
    
    # Process
    downloader.process_tweets(tweet_ids, limit=args.limit)
    
    # Print summary
    downloader.print_summary()


if __name__ == "__main__":
    main()

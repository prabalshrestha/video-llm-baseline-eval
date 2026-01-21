#!/usr/bin/env python3
"""
Check for Duplicate Video Records

This script checks for duplicate video records in the database BEFORE migration.
Run this to identify any existing duplicates that need to be cleaned up.
"""

import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, List
import sys

sys.path.insert(0, str(Path(__file__).parent))

from database import get_session, MediaMetadata

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DuplicateChecker:
    """Check for duplicate video records in database."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.stats = {
            "total_records": 0,
            "unique_tweets": 0,
            "tweets_with_duplicates": 0,
            "duplicate_records": 0,
            "records_to_delete": 0,
        }

    def check_duplicates(self) -> Dict[str, List]:
        """
        Check for duplicate video records for the same tweet.
        
        In the OLD schema (before migration), each tweet should have only ONE
        MediaMetadata record. This checks for violations.
        
        Returns:
            Dict mapping tweet_id -> list of MediaMetadata records
        """
        logger.info("Checking for duplicate video records...")
        
        with get_session() as session:
            # Get all video records
            all_videos = session.query(MediaMetadata).filter(
                MediaMetadata.media_type == 'video'
            ).all()
            
            self.stats["total_records"] = len(all_videos)
            logger.info(f"Found {len(all_videos)} video records in database")
            
            # Group by tweet_id
            videos_by_tweet = defaultdict(list)
            for video in all_videos:
                videos_by_tweet[str(video.tweet_id)].append(video)
            
            self.stats["unique_tweets"] = len(videos_by_tweet)
            
            # Find duplicates
            duplicates = {}
            for tweet_id, videos in videos_by_tweet.items():
                if len(videos) > 1:
                    duplicates[tweet_id] = videos
                    self.stats["tweets_with_duplicates"] += 1
                    self.stats["duplicate_records"] += len(videos) - 1
            
            if duplicates:
                logger.warning(
                    f"⚠️  Found {len(duplicates)} tweets with duplicate video records!"
                )
                logger.info(f"Total duplicate records: {self.stats['duplicate_records']}")
                
                # Show details
                for tweet_id, videos in list(duplicates.items())[:10]:
                    logger.warning(f"\nTweet {tweet_id} has {len(videos)} records:")
                    for i, video in enumerate(videos, 1):
                        logger.warning(f"  {i}. media_id={video.media_id}")
                        logger.warning(f"     local_path={video.local_path}")
                        logger.warning(f"     duration={video.duration_ms}ms")
                
                if len(duplicates) > 10:
                    logger.warning(f"\n... and {len(duplicates) - 10} more tweets with duplicates")
            else:
                logger.info("✓ No duplicate records found! All tweets have exactly one video.")
            
            return duplicates

    def resolve_duplicates(self, duplicates: Dict[str, List]):
        """
        Resolve duplicates by keeping only one record per tweet.
        
        Strategy:
        1. Keep the record with local_path set (downloaded video)
        2. If multiple have local_path, keep the one with valid file
        3. If none have valid file, keep the first one
        
        Args:
            duplicates: Dict mapping tweet_id -> list of duplicate records
        """
        if not duplicates:
            logger.info("No duplicates to resolve")
            return
        
        if self.dry_run:
            logger.info("\n" + "="*60)
            logger.info("DRY RUN - Showing what would be deleted")
            logger.info("="*60)
        else:
            logger.info("\n" + "="*60)
            logger.info("LIVE MODE - Deleting duplicate records")
            logger.info("="*60)
        
        with get_session() as session:
            for tweet_id, videos in duplicates.items():
                logger.info(f"\nTweet {tweet_id}: {len(videos)} records")
                
                # Sort by priority:
                # 1. Has local_path AND file exists
                # 2. Has local_path (even if file doesn't exist)
                # 3. No local_path
                def priority(video):
                    if video.local_path:
                        if Path(video.local_path).exists():
                            return 0  # Highest priority
                        return 1
                    return 2  # Lowest priority
                
                sorted_videos = sorted(videos, key=priority)
                
                # Keep the first (highest priority)
                to_keep = sorted_videos[0]
                to_delete = sorted_videos[1:]
                
                logger.info(f"  ✓ Keeping: media_id={to_keep.media_id}, path={to_keep.local_path}")
                
                for video in to_delete:
                    logger.info(f"  ✗ Deleting: media_id={video.media_id}, path={video.local_path}")
                    
                    if not self.dry_run:
                        try:
                            session.delete(video)
                            session.commit()
                            self.stats["records_to_delete"] += 1
                        except Exception as e:
                            logger.error(f"    Failed to delete: {e}")
                            session.rollback()
                    else:
                        self.stats["records_to_delete"] += 1

    def print_summary(self):
        """Print summary of findings."""
        logger.info("\n" + "="*60)
        logger.info("SUMMARY")
        logger.info("="*60)
        logger.info(f"Total video records: {self.stats['total_records']}")
        logger.info(f"Unique tweets: {self.stats['unique_tweets']}")
        logger.info(f"Tweets with duplicates: {self.stats['tweets_with_duplicates']}")
        logger.info(f"Duplicate records found: {self.stats['duplicate_records']}")
        
        if self.stats['records_to_delete'] > 0:
            logger.info(f"Records to delete: {self.stats['records_to_delete']}")
        
        logger.info("="*60)
        
        if self.stats['tweets_with_duplicates'] > 0:
            if self.dry_run:
                logger.warning("\n⚠️  Duplicates found! Run with --fix to clean them up.")
            else:
                logger.info("\n✓ Duplicates cleaned up!")
        else:
            logger.info("\n✓ No duplicates found. Database is clean!")

    def run(self, fix: bool = False):
        """Run duplicate check and optionally fix."""
        logger.info("="*60)
        logger.info("DUPLICATE VIDEO RECORD CHECKER")
        logger.info("="*60)
        logger.info(f"Mode: {'FIX' if fix else 'CHECK ONLY'}")
        logger.info("")
        
        # Check for duplicates
        duplicates = self.check_duplicates()
        
        # Resolve if requested
        if fix and duplicates:
            self.resolve_duplicates(duplicates)
        elif duplicates:
            logger.info("\nTo fix duplicates, run: python check_duplicates.py --fix")
        
        # Print summary
        self.print_summary()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Check for duplicate video records in database"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix duplicates by deleting extra records (keeps best one)"
    )
    
    args = parser.parse_args()
    
    checker = DuplicateChecker(dry_run=not args.fix)
    checker.run(fix=args.fix)


if __name__ == "__main__":
    main()

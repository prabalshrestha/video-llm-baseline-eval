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

from database import get_session
from sqlalchemy import text

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
        
        Uses raw SQL to work with current schema (before migration).
        
        Returns:
            Dict mapping tweet_id -> list of dicts with record info
        """
        logger.info("Checking for duplicate video records...")
        
        with get_session() as session:
            # Use raw SQL to avoid ORM issues with schema mismatch
            # Query for tweets with multiple video records
            sql = text("""
                SELECT 
                    tweet_id,
                    COUNT(*) as record_count,
                    array_agg(media_id::text) as media_ids,
                    array_agg(local_path::text) as local_paths,
                    array_agg(duration_ms) as durations
                FROM media_metadata
                WHERE media_type = 'video'
                GROUP BY tweet_id
            """)
            
            result = session.execute(sql)
            rows = result.fetchall()
            
            total_records = sum(row[1] for row in rows)  # Sum of all record_counts
            self.stats["total_records"] = total_records
            self.stats["unique_tweets"] = len(rows)
            
            logger.info(f"Found {total_records} video records in database")
            logger.info(f"Spread across {len(rows)} unique tweets")
            
            # Find duplicates (tweets with count > 1)
            duplicates = {}
            for row in rows:
                tweet_id = str(row[0])
                record_count = row[1]
                
                if record_count > 1:
                    # Store as list of dicts for easier handling
                    media_ids = row[2]
                    local_paths = row[3]
                    durations = row[4]
                    
                    records = []
                    for i in range(record_count):
                        records.append({
                            'tweet_id': tweet_id,
                            'media_id': media_ids[i] if media_ids else None,
                            'local_path': local_paths[i] if local_paths else None,
                            'duration_ms': durations[i] if durations else None,
                        })
                    
                    duplicates[tweet_id] = records
                    self.stats["tweets_with_duplicates"] += 1
                    self.stats["duplicate_records"] += record_count - 1
            
            if duplicates:
                logger.warning(
                    f"⚠️  Found {len(duplicates)} tweets with duplicate video records!"
                )
                logger.info(f"Total duplicate records: {self.stats['duplicate_records']}")
                
                # Show details
                for tweet_id, records in list(duplicates.items())[:10]:
                    logger.warning(f"\nTweet {tweet_id} has {len(records)} records:")
                    for i, record in enumerate(records, 1):
                        logger.warning(f"  {i}. media_id={record['media_id']}")
                        logger.warning(f"     local_path={record['local_path']}")
                        logger.warning(f"     duration={record['duration_ms']}ms")
                
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
        
        Uses raw SQL to work with current schema (before migration).
        
        Args:
            duplicates: Dict mapping tweet_id -> list of duplicate records (dicts)
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
            for tweet_id, records in duplicates.items():
                logger.info(f"\nTweet {tweet_id}: {len(records)} records")
                
                # Sort by priority:
                # 1. Has local_path AND file exists
                # 2. Has local_path (even if file doesn't exist)
                # 3. No local_path
                def priority(record):
                    local_path = record.get('local_path')
                    if local_path:
                        if Path(local_path).exists():
                            return 0  # Highest priority
                        return 1
                    return 2  # Lowest priority
                
                sorted_records = sorted(records, key=priority)
                
                # Keep the first (highest priority)
                to_keep = sorted_records[0]
                to_delete = sorted_records[1:]
                
                logger.info(f"  ✓ Keeping: media_id={to_keep['media_id']}, path={to_keep['local_path']}")
                
                for record in to_delete:
                    logger.info(f"  ✗ Deleting: media_id={record['media_id']}, path={record['local_path']}")
                    
                    if not self.dry_run:
                        try:
                            # Delete using raw SQL since we can't use ORM
                            # In old schema, tweet_id is primary key
                            # But we have duplicates, so we need to identify by other fields
                            # Use media_id to uniquely identify the record to delete
                            if record['media_id']:
                                sql = text("""
                                    DELETE FROM media_metadata 
                                    WHERE tweet_id = :tweet_id 
                                    AND media_id = :media_id
                                """)
                                session.execute(sql, {
                                    'tweet_id': int(tweet_id),
                                    'media_id': record['media_id']
                                })
                            else:
                                # If no media_id, use local_path
                                sql = text("""
                                    DELETE FROM media_metadata 
                                    WHERE tweet_id = :tweet_id 
                                    AND local_path = :local_path
                                """)
                                session.execute(sql, {
                                    'tweet_id': int(tweet_id),
                                    'local_path': record['local_path']
                                })
                            
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

#!/usr/bin/env python3
"""
Reset Local Paths and Prepare for Re-download

This script:
1. Saves list of tweet IDs that have videos downloaded
2. Clears all local_path values in database
3. Optionally deletes the video files
4. Provides command to re-download
"""

import logging
from pathlib import Path
import sys
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from database import get_session
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def save_tweet_ids_to_redownload(output_file="tweets_to_redownload.json"):
    """Save list of tweet IDs that currently have videos."""
    logger.info("Step 1: Saving list of tweet IDs with downloaded videos...")
    
    with get_session() as session:
        sql = text("""
            SELECT tweet_id, local_path
            FROM media_metadata
            WHERE media_type = 'video'
            AND local_path IS NOT NULL
            ORDER BY tweet_id
        """)
        
        result = session.execute(sql)
        records = result.fetchall()
        
        tweet_ids = [str(row[0]) for row in records]
        
        # Save to file
        data = {
            "timestamp": datetime.now().isoformat(),
            "count": len(tweet_ids),
            "tweet_ids": tweet_ids
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"✓ Saved {len(tweet_ids)} tweet IDs to {output_file}")
        return tweet_ids


def clear_local_paths(dry_run=True):
    """Clear all local_path values in database."""
    logger.info(f"\nStep 2: Clearing local_path values (dry_run={dry_run})...")
    
    with get_session() as session:
        # First count
        sql_count = text("""
            SELECT COUNT(*)
            FROM media_metadata
            WHERE media_type = 'video'
            AND local_path IS NOT NULL
        """)
        
        count = session.execute(sql_count).scalar()
        logger.info(f"Found {count} records with local_path set")
        
        if not dry_run:
            # Clear them
            sql_clear = text("""
                UPDATE media_metadata
                SET local_path = NULL
                WHERE media_type = 'video'
                AND local_path IS NOT NULL
            """)
            
            session.execute(sql_clear)
            session.commit()
            logger.info(f"✓ Cleared {count} local_path values")
        else:
            logger.info(f"[DRY RUN] Would clear {count} local_path values")
        
        return count


def delete_video_files(videos_dir="data/videos", dry_run=True):
    """Optionally delete all video files."""
    logger.info(f"\nStep 3: Deleting video files (dry_run={dry_run})...")
    
    videos_dir = Path(videos_dir)
    
    # Find all video files
    video_files = list(videos_dir.glob("*.mp4")) + list(videos_dir.glob("*.webm"))
    info_files = list(videos_dir.glob("*.info.json"))
    
    logger.info(f"Found {len(video_files)} video files")
    logger.info(f"Found {len(info_files)} info.json files")
    
    if not dry_run:
        deleted_videos = 0
        deleted_info = 0
        
        for f in video_files:
            try:
                f.unlink()
                deleted_videos += 1
            except Exception as e:
                logger.warning(f"Failed to delete {f.name}: {e}")
        
        for f in info_files:
            try:
                f.unlink()
                deleted_info += 1
            except Exception as e:
                logger.warning(f"Failed to delete {f.name}: {e}")
        
        logger.info(f"✓ Deleted {deleted_videos} video files")
        logger.info(f"✓ Deleted {deleted_info} info files")
    else:
        logger.info(f"[DRY RUN] Would delete {len(video_files)} video files")
        logger.info(f"[DRY RUN] Would delete {len(info_files)} info files")


def print_redownload_command(tweet_ids_file="tweets_to_redownload.json"):
    """Print command to re-download videos."""
    logger.info("\n" + "="*70)
    logger.info("NEXT STEPS")
    logger.info("="*70)
    logger.info("\nTo re-download the videos:")
    logger.info(f"\n1. The tweet IDs are saved in: {tweet_ids_file}")
    logger.info(f"\n2. Re-download with updated download script:")
    logger.info("   python scripts/data_processing/download_videos.py --force")
    logger.info("\n   This will:")
    logger.info("   - Use the NEW naming convention (TWEETID_1.mp4)")
    logger.info("   - Download only videos where local_path is NULL")
    logger.info("   - Update database with correct paths")
    logger.info("\n3. Or download specific tweets:")
    logger.info("   python scripts/data_processing/download_videos.py --limit 50")
    logger.info("="*70)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Reset local paths and prepare for re-download"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--delete-files",
        action="store_true",
        help="Also delete the video files from disk"
    )
    parser.add_argument(
        "--output",
        default="tweets_to_redownload.json",
        help="Output file for tweet IDs (default: tweets_to_redownload.json)"
    )
    
    args = parser.parse_args()
    
    logger.info("="*70)
    logger.info("RESET LOCAL PATHS AND PREPARE FOR RE-DOWNLOAD")
    logger.info("="*70)
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info(f"Delete files: {'YES' if args.delete_files else 'NO'}")
    logger.info("")
    
    # Step 1: Save tweet IDs
    tweet_ids = save_tweet_ids_to_redownload(args.output)
    
    # Step 2: Clear database paths
    count = clear_local_paths(dry_run=args.dry_run)
    
    # Step 3: Optionally delete files
    if args.delete_files:
        delete_video_files(dry_run=args.dry_run)
    
    # Print summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    logger.info(f"Tweet IDs saved: {len(tweet_ids)}")
    logger.info(f"Database paths cleared: {count if not args.dry_run else f'{count} (would clear)'}")
    
    if args.delete_files:
        logger.info(f"Video files: {'Deleted' if not args.dry_run else 'Would delete'}")
    else:
        logger.info(f"Video files: Kept on disk (use --delete-files to remove)")
    
    logger.info("="*70)
    
    if args.dry_run:
        logger.info("\n⚠️  This was a DRY RUN. No changes were made.")
        logger.info("Run without --dry-run to apply changes.")
    else:
        logger.info("\n✓ Database reset complete!")
        print_redownload_command(args.output)


if __name__ == "__main__":
    main()

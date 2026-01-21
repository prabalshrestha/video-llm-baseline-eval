#!/usr/bin/env python3
"""
Verify and Fix Database Mappings

This script checks if database local_path mappings are correct after file renaming.
If not, it updates them to match the current renamed files.
"""

import re
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from database import get_session
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def verify_and_fix_mappings(videos_dir="data/videos", fix=False):
    """
    Verify and optionally fix database mappings.
    
    Args:
        videos_dir: Path to videos directory
        fix: Whether to fix incorrect mappings
    """
    videos_dir = Path(videos_dir)
    
    logger.info("="*60)
    logger.info("DATABASE MAPPING VERIFICATION")
    logger.info("="*60)
    logger.info(f"Videos directory: {videos_dir}")
    logger.info(f"Mode: {'FIX' if fix else 'CHECK ONLY'}")
    logger.info("")
    
    # Step 1: Get all renamed video files
    logger.info("Step 1: Scanning video files...")
    video_files = {}
    for video_file in videos_dir.glob("*.mp4"):
        # Match new format: TWEETID_INDEX.mp4
        match = re.match(r'^(\d+)_(\d+)\.mp4$', video_file.name)
        if match:
            tweet_id = match.group(1)
            video_index = int(match.group(2))
            
            if tweet_id not in video_files:
                video_files[tweet_id] = []
            video_files[tweet_id].append({
                'path': str(video_file.absolute()),
                'index': video_index,
                'filename': video_file.name
            })
    
    logger.info(f"Found {sum(len(v) for v in video_files.values())} renamed video files")
    logger.info(f"Covering {len(video_files)} unique tweets")
    
    # Step 2: Check database mappings
    logger.info("\nStep 2: Checking database mappings...")
    
    with get_session() as session:
        # Get all video records from database - but limit to those with local_path
        # to avoid checking 40k records
        sql = text("""
            SELECT tweet_id, local_path
            FROM media_metadata
            WHERE media_type = 'video'
            AND local_path IS NOT NULL
        """)
        
        result = session.execute(sql)
        db_records = result.fetchall()
        
        logger.info(f"Found {len(db_records)} video records in database")
        
        # Check each record
        correct = 0
        incorrect = 0
        missing = 0
        to_update = []
        
        for row in db_records:
            tweet_id = str(row[0])
            db_path = row[1]
            
            # Check if tweet has renamed files
            if tweet_id not in video_files:
                logger.warning(f"⚠️  Tweet {tweet_id} in DB but no renamed files found")
                missing += 1
                continue
            
            # Get expected path (first video for this tweet)
            expected_path = video_files[tweet_id][0]['path']
            
            # Compare paths
            if db_path == expected_path:
                correct += 1
            else:
                incorrect += 1
                logger.warning(f"✗ MISMATCH: Tweet {tweet_id}")
                logger.warning(f"  DB has: {db_path}")
                logger.warning(f"  Should be: {expected_path}")
                
                to_update.append({
                    'tweet_id': int(tweet_id),
                    'old_path': db_path,
                    'new_path': expected_path
                })
        
        # Check reverse: do renamed files have DB records?
        logger.info("\nChecking if renamed files have database records...")
        files_without_db = []
        for tweet_id, files in video_files.items():
            # Check if this tweet_id exists in database
            found_in_db = False
            for row in db_records:
                if str(row[0]) == tweet_id:
                    found_in_db = True
                    break
            
            if not found_in_db:
                files_without_db.append(tweet_id)
                logger.warning(f"⚠️  File {files[0]['filename']} has no database record!")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("VERIFICATION RESULTS")
        logger.info("="*60)
        logger.info(f"✓ Correct mappings: {correct}")
        logger.info(f"✗ Incorrect mappings: {incorrect}")
        logger.info(f"⚠ DB records without files: {missing}")
        logger.info(f"⚠ Renamed files without DB: {len(files_without_db)}")
        logger.info(f"Total DB records: {len(db_records)}")
        logger.info(f"Total renamed files: {sum(len(v) for v in video_files.values())}")
        logger.info("="*60)
        
        # Fix if requested
        if fix and to_update:
            logger.info(f"\nFixing {len(to_update)} incorrect mappings...")
            
            for update in to_update:
                try:
                    update_sql = text("""
                        UPDATE media_metadata
                        SET local_path = :new_path
                        WHERE tweet_id = :tweet_id
                    """)
                    session.execute(update_sql, {
                        'new_path': update['new_path'],
                        'tweet_id': update['tweet_id']
                    })
                    logger.info(f"✓ Updated: Tweet {update['tweet_id']}")
                except Exception as e:
                    logger.error(f"✗ Failed to update tweet {update['tweet_id']}: {e}")
                    session.rollback()
                    return False
            
            # Commit all updates
            try:
                session.commit()
                logger.info(f"\n✓ Successfully updated {len(to_update)} database records!")
                return True
            except Exception as e:
                logger.error(f"✗ Failed to commit updates: {e}")
                session.rollback()
                return False
        
        elif fix and not to_update:
            logger.info("\n✓ No updates needed - all mappings are correct!")
            return True
        
        elif not fix and to_update:
            logger.info(f"\n⚠️  Found {incorrect} incorrect mappings.")
            logger.info("Run with --fix to update them:")
            logger.info(f"  python {Path(__file__).name} --fix")
            return False
        
        else:
            logger.info("\n✓ All mappings are correct!")
            return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verify and fix database video path mappings"
    )
    parser.add_argument(
        "--videos-dir",
        default="data/videos",
        help="Path to videos directory (default: data/videos)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix incorrect mappings in database"
    )
    
    args = parser.parse_args()
    
    success = verify_and_fix_mappings(
        videos_dir=args.videos_dir,
        fix=args.fix
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Emergency Recovery Script

This script helps recover from a failed migration by:
1. Identifying what state your files are in
2. Providing options to fix or reverse
"""

import re
import json
import logging
from pathlib import Path
from collections import defaultdict
import sys

sys.path.insert(0, str(Path(__file__).parent))

from database import get_session
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def assess_situation(videos_dir="data/videos"):
    """Assess the current state of video files and database."""
    videos_dir = Path(videos_dir)
    
    logger.info("="*70)
    logger.info("EMERGENCY RECOVERY - SITUATION ASSESSMENT")
    logger.info("="*70)
    
    # Check video files
    all_files = list(videos_dir.glob("*.mp4"))
    old_format = []  # video_NNN_TWEETID.mp4
    new_format = []  # TWEETID_N.mp4
    unknown_format = []
    
    for f in all_files:
        if re.match(r'^video_\d+_(\d+)\.mp4$', f.name):
            match = re.match(r'^video_\d+_(\d+)\.mp4$', f.name)
            old_format.append((f, match.group(1)))
        elif re.match(r'^(\d+)_(\d+)\.mp4$', f.name):
            match = re.match(r'^(\d+)_(\d+)\.mp4$', f.name)
            new_format.append((f, match.group(1)))
        else:
            unknown_format.append(f)
    
    logger.info(f"\n📁 VIDEO FILES:")
    logger.info(f"  Old format (video_NNN_TWEETID.mp4): {len(old_format)}")
    logger.info(f"  New format (TWEETID_N.mp4): {len(new_format)}")
    logger.info(f"  Unknown format: {len(unknown_format)}")
    logger.info(f"  Total: {len(all_files)}")
    
    # Show examples
    if old_format:
        logger.info(f"\n  Old format examples:")
        for f, _ in old_format[:3]:
            logger.info(f"    - {f.name}")
    
    if new_format:
        logger.info(f"\n  New format examples:")
        for f, _ in new_format[:3]:
            logger.info(f"    - {f.name}")
    
    if unknown_format:
        logger.info(f"\n  Unknown format examples:")
        for f in unknown_format[:3]:
            logger.info(f"    - {f.name}")
    
    # Check database
    with get_session() as session:
        sql = text("""
            SELECT tweet_id, local_path
            FROM media_metadata
            WHERE media_type = 'video'
            AND local_path IS NOT NULL
            LIMIT 1000
        """)
        
        result = session.execute(sql)
        db_records = result.fetchall()
        
        db_old = 0
        db_new = 0
        db_missing = 0
        
        for row in db_records:
            tweet_id = str(row[0])
            path = row[1]
            
            if not path:
                continue
                
            filename = Path(path).name
            
            if re.match(r'^video_\d+_\d+\.mp4$', filename):
                db_old += 1
            elif re.match(r'^\d+_\d+\.mp4$', filename):
                db_new += 1
            
            if not Path(path).exists():
                db_missing += 1
        
        logger.info(f"\n💾 DATABASE (sample of {len(db_records)} records):")
        logger.info(f"  Points to old format: {db_old}")
        logger.info(f"  Points to new format: {db_new}")
        logger.info(f"  Points to missing files: {db_missing}")
    
    # Determine situation
    logger.info(f"\n{'='*70}")
    logger.info("DIAGNOSIS:")
    logger.info("="*70)
    
    if len(new_format) > 0 and len(old_format) == 0:
        logger.info("✅ Migration completed - all files in new format")
        logger.info("❌ But database might not be updated")
        logger.info("\n📋 RECOMMENDATION: Run database fix")
        logger.info("   python verify_and_fix_db_mappings.py --fix")
        return "migration_complete_db_broken"
        
    elif len(old_format) > 0 and len(new_format) == 0:
        logger.info("✅ All files still in old format")
        logger.info("✅ Database likely correct")
        logger.info("\n📋 RECOMMENDATION: You're safe! Nothing was changed.")
        logger.info("   Run migration again if desired: python fix_video_mapping.py")
        return "no_migration"
        
    elif len(old_format) > 0 and len(new_format) > 0:
        logger.info("⚠️  MIXED STATE - Some files renamed, some not")
        logger.info("❌ This is problematic")
        logger.info("\n📋 RECOMMENDATION: Finish the rename or reverse it")
        logger.info("   Option 1: python fix_video_mapping.py (continue renaming)")
        logger.info("   Option 2: [Need to create reverse script]")
        return "mixed_state"
        
    else:
        logger.info("⚠️  No video files found in expected formats")
        return "unknown"


def create_reverse_mapping(videos_dir="data/videos"):
    """Create a mapping to reverse the rename."""
    videos_dir = Path(videos_dir)
    
    logger.info("\n" + "="*70)
    logger.info("CREATING REVERSE MAPPING")
    logger.info("="*70)
    
    # Find all info.json files
    info_files = list(videos_dir.glob("*.info.json"))
    
    reverse_map = {}
    
    for info_file in info_files:
        try:
            # Read info to get original tweet_id
            with open(info_file) as f:
                info = json.load(f)
            
            # Get corresponding video file
            video_file = info_file.with_suffix(".mp4")
            if not video_file.exists():
                continue
            
            # Check if it's in new format
            match = re.match(r'^(\d+)_(\d+)\.mp4$', video_file.name)
            if match:
                tweet_id = match.group(1)
                # Store mapping for reversal
                reverse_map[str(video_file)] = info
                
        except Exception as e:
            logger.debug(f"Could not process {info_file}: {e}")
    
    logger.info(f"Found {len(reverse_map)} videos that can be reversed")
    
    return reverse_map


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Emergency recovery tool")
    parser.add_argument(
        "--videos-dir",
        default="data/videos",
        help="Path to videos directory"
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Attempt to reverse the rename (NOT IMPLEMENTED YET)"
    )
    
    args = parser.parse_args()
    
    # Assess situation
    state = assess_situation(args.videos_dir)
    
    logger.info(f"\n{'='*70}")
    logger.info("NEXT STEPS:")
    logger.info("="*70)
    logger.info("1. Review the diagnosis above")
    logger.info("2. Choose the recommended action")
    logger.info("3. Contact support if unsure")
    logger.info("="*70)


if __name__ == "__main__":
    main()

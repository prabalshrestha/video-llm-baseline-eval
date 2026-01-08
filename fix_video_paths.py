#!/usr/bin/env python3
"""
Fix video file paths in database.

This script updates the local_path column in media_metadata table to use
the current environment's video directory instead of hardcoded paths from
the original system.

Usage:
    python3 fix_video_paths.py
    python3 fix_video_paths.py --dry-run  # Preview changes without applying
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database import get_session
from database.models import MediaMetadata

load_dotenv()


def get_video_directory():
    """Get the video directory, respecting VIDEO_DOWNLOAD_PATH env var."""
    video_path_env = os.getenv("VIDEO_DOWNLOAD_PATH")
    
    if video_path_env:
        video_dir = Path(video_path_env)
        print(f"Using VIDEO_DOWNLOAD_PATH: {video_dir}")
    else:
        video_dir = Path(__file__).parent / "data" / "videos"
        print(f"Using default path: {video_dir}")
    
    return video_dir


def fix_video_paths(dry_run=False):
    """
    Fix video paths in database.
    
    Args:
        dry_run: If True, only show what would be changed without applying
    """
    print("=" * 70)
    print("Fix Video Paths in Database")
    print("=" * 70)
    
    # Get target video directory
    video_dir = get_video_directory()
    
    if not video_dir.exists():
        print(f"\n⚠️  Warning: Video directory does not exist: {video_dir}")
        print("Creating directory...")
        video_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nTarget video directory: {video_dir.absolute()}")
    print()
    
    with get_session() as session:
        # Get all media metadata with local_path set
        media_records = session.query(MediaMetadata).filter(
            MediaMetadata.local_path.isnot(None)
        ).all()
        
        print(f"Found {len(media_records)} media records with local_path set")
        print()
        
        stats = {
            "total": len(media_records),
            "already_correct": 0,
            "updated": 0,
            "file_not_found": 0,
            "errors": 0
        }
        
        for media in media_records:
            old_path = media.local_path
            old_path_obj = Path(old_path)
            
            # Extract just the filename
            filename = old_path_obj.name
            
            # Construct new path using current video directory
            new_path = video_dir / filename
            new_path_str = str(new_path.absolute())
            
            # Check if already correct
            if old_path == new_path_str:
                stats["already_correct"] += 1
                continue
            
            # Check if file exists in new location
            if not new_path.exists():
                print(f"⚠️  File not found: {filename}")
                print(f"   Old path: {old_path}")
                print(f"   New path: {new_path_str}")
                print()
                stats["file_not_found"] += 1
                continue
            
            # Update path
            print(f"✓ Updating: {filename}")
            print(f"  From: {old_path}")
            print(f"  To:   {new_path_str}")
            print()
            
            if not dry_run:
                try:
                    media.local_path = new_path_str
                    session.commit()
                    stats["updated"] += 1
                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    session.rollback()
                    stats["errors"] += 1
            else:
                stats["updated"] += 1  # Count what would be updated
        
        # Summary
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"Total records:        {stats['total']}")
        print(f"Already correct:      {stats['already_correct']}")
        print(f"{'Would update' if dry_run else 'Updated'}:           {stats['updated']}")
        print(f"File not found:       {stats['file_not_found']}")
        print(f"Errors:               {stats['errors']}")
        print()
        
        if dry_run:
            print("✓ Dry run complete - no changes were made")
            print("  Run without --dry-run to apply changes")
        else:
            print(f"✓ Updated {stats['updated']} paths successfully!")
        
        if stats["file_not_found"] > 0:
            print()
            print(f"⚠️  Warning: {stats['file_not_found']} files not found in {video_dir}")
            print("   Make sure videos are synced to this location")
        
        print("=" * 70)
        
        return stats


def main():
    parser = argparse.ArgumentParser(
        description="Fix video file paths in database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    
    args = parser.parse_args()
    
    try:
        stats = fix_video_paths(dry_run=args.dry_run)
        
        # Exit with error code if there were issues
        if stats["file_not_found"] > 0:
            print("\n⚠️  Some files were not found. Sync videos and run again.")
            sys.exit(1)
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


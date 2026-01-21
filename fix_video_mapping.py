#!/usr/bin/env python3
"""
Fix Video Mapping and Rename Files

This script:
1. Renames all video files from old format (video_XXX_TWEETID.mp4) to new format (TWEETID_1.mp4)
2. Updates database MediaMetadata.local_path to match renamed files
3. Handles multiple videos per tweet with sequential numbering

Run this BEFORE updating the database schema.
"""

import re
import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent))

from database import get_session
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VideoMappingFixer:
    """Fix video file names and database mappings."""

    def __init__(self, videos_dir: str = "data/videos", dry_run: bool = False):
        self.videos_dir = Path(videos_dir)
        self.dry_run = dry_run
        self.stats = {
            "total_files": 0,
            "renamed": 0,
            "skipped": 0,
            "errors": 0,
            "db_updated": 0,
            "db_errors": 0,
        }

    def extract_tweet_id_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract tweet ID from old format filename.

        Formats supported:
        - video_001_1234567890.mp4 -> 1234567890
        - video_001_1234567890.info.json -> 1234567890

        Args:
            filename: Video filename

        Returns:
            Tweet ID or None if not found
        """
        # Match pattern: video_XXX_TWEETID.ext
        match = re.search(r"video_\d+_(\d+)\.(mp4|webm|info\.json)", filename)
        if match:
            return match.group(1)
        return None

    def scan_existing_files(self) -> Dict[str, List[Path]]:
        """
        Scan video directory and group files by tweet ID.

        Returns:
            Dict mapping tweet_id -> list of video files
        """
        logger.info(f"Scanning video directory: {self.videos_dir}")

        video_files = list(self.videos_dir.glob("video_*_*.mp4")) + list(
            self.videos_dir.glob("video_*_*.webm")
        )

        self.stats["total_files"] = len(video_files)
        logger.info(f"Found {len(video_files)} video files")

        # Group by tweet ID
        files_by_tweet = defaultdict(list)

        for video_file in video_files:
            tweet_id = self.extract_tweet_id_from_filename(video_file.name)
            if tweet_id:
                files_by_tweet[tweet_id].append(video_file)
            else:
                logger.warning(f"Could not extract tweet ID from: {video_file.name}")
                self.stats["skipped"] += 1

        logger.info(f"Grouped into {len(files_by_tweet)} unique tweets")

        # Log tweets with multiple videos
        multi_video_tweets = [
            tid for tid, files in files_by_tweet.items() if len(files) > 1
        ]
        if multi_video_tweets:
            logger.info(f"Found {len(multi_video_tweets)} tweets with multiple videos:")
            for tid in multi_video_tweets[:5]:
                logger.info(f"  Tweet {tid}: {len(files_by_tweet[tid])} videos")

        return files_by_tweet

    def rename_files(self, files_by_tweet: Dict[str, List[Path]]) -> Dict[str, str]:
        """
        Rename video files to new format: TWEETID_N.ext

        Args:
            files_by_tweet: Dict mapping tweet_id -> list of video files

        Returns:
            Dict mapping old_path -> new_path
        """
        rename_map = {}

        for tweet_id, video_files in sorted(files_by_tweet.items()):
            # Sort by filename to ensure consistent ordering
            video_files.sort(key=lambda f: f.name)

            for idx, old_file in enumerate(video_files, start=1):
                # Generate new filename: TWEETID_1.mp4, TWEETID_2.mp4, etc.
                extension = old_file.suffix  # .mp4 or .webm
                new_filename = f"{tweet_id}_{idx}{extension}"
                new_path = self.videos_dir / new_filename

                # Also rename .info.json if it exists
                old_info = old_file.with_suffix(".info.json")
                new_info = new_path.with_suffix(".info.json")

                # Rename video file
                if old_file.exists():
                    if self.dry_run:
                        logger.info(
                            f"[DRY RUN] Would rename: {old_file.name} -> {new_filename}"
                        )
                    else:
                        if new_path.exists() and new_path != old_file:
                            logger.warning(f"Target already exists: {new_filename}")
                            self.stats["skipped"] += 1
                            continue

                        try:
                            old_file.rename(new_path)
                            logger.info(f"✓ Renamed: {old_file.name} -> {new_filename}")
                            rename_map[str(old_file.absolute())] = str(
                                new_path.absolute()
                            )
                            self.stats["renamed"] += 1
                        except Exception as e:
                            logger.error(f"✗ Failed to rename {old_file.name}: {e}")
                            self.stats["errors"] += 1

                # Rename info.json if it exists
                if old_info.exists() and not self.dry_run:
                    try:
                        old_info.rename(new_info)
                        logger.debug(
                            f"  + Renamed info: {old_info.name} -> {new_info.name}"
                        )
                    except Exception as e:
                        logger.warning(f"  - Failed to rename info file: {e}")

        return rename_map

    def update_database(
        self, rename_map: Dict[str, str], files_by_tweet: Dict[str, List[Path]]
    ):
        """
        Update database MediaMetadata.local_path to match renamed files.

        Uses raw SQL to work with current schema (before migration).

        Args:
            rename_map: Dict mapping old_path -> new_path
            files_by_tweet: Dict mapping tweet_id -> list of original video files
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would update database mappings")
            return

        logger.info("Updating database mappings...")

        with get_session() as session:
            # Get all video records using raw SQL
            sql = text(
                """
                SELECT tweet_id, local_path
                FROM media_metadata
                WHERE media_type = 'video'
            """
            )

            result = session.execute(sql)
            all_media = result.fetchall()

            logger.info(f"Found {len(all_media)} video records in database")

            for row in all_media:
                tweet_id = str(row[0])
                old_db_path = row[1]

                # Check if this tweet has videos in our files_by_tweet mapping
                if tweet_id not in files_by_tweet:
                    logger.warning(f"Tweet {tweet_id} in DB but no video files found")
                    continue

                # Get the new path (first video for this tweet, since DB is one-to-one)
                video_files = files_by_tweet[tweet_id]
                old_file = video_files[0]  # Use first video

                # Find the new path in rename_map
                old_path = str(old_file.absolute())
                new_path = None

                # Check rename_map
                if old_path in rename_map:
                    new_path = rename_map[old_path]
                else:
                    # File might not have been renamed (already in correct format)
                    # Generate expected new path
                    extension = old_file.suffix
                    new_filename = f"{tweet_id}_1{extension}"
                    new_path = str((self.videos_dir / new_filename).absolute())

                # Update database
                if new_path and Path(new_path).exists():
                    try:
                        update_sql = text(
                            """
                            UPDATE media_metadata
                            SET local_path = :new_path
                            WHERE tweet_id = :tweet_id
                        """
                        )
                        session.execute(
                            update_sql,
                            {"new_path": new_path, "tweet_id": int(tweet_id)},
                        )
                        session.commit()
                        logger.info(f"✓ Updated DB: {tweet_id}")
                        logger.debug(f"  Old: {old_db_path}")
                        logger.debug(f"  New: {new_path}")
                        self.stats["db_updated"] += 1
                    except Exception as e:
                        logger.error(f"✗ Failed to update DB for {tweet_id}: {e}")
                        session.rollback()
                        self.stats["db_errors"] += 1
                else:
                    logger.warning(f"New path doesn't exist for {tweet_id}: {new_path}")
                    self.stats["db_errors"] += 1

    def verify_mappings(self):
        """
        Verify that all database mappings point to existing files.

        Uses raw SQL to work with current schema (before migration).
        """
        logger.info("\nVerifying database mappings...")

        with get_session() as session:
            # Get all video records with local_path using raw SQL
            sql = text(
                """
                SELECT tweet_id, local_path
                FROM media_metadata
                WHERE media_type = 'video'
                AND local_path IS NOT NULL
            """
            )

            result = session.execute(sql)
            all_media = result.fetchall()

            correct = 0
            incorrect = 0

            for row in all_media:
                tweet_id = str(row[0])
                local_path = row[1]

                # Check if file exists
                if not Path(local_path).exists():
                    logger.error(
                        f"✗ MISMATCH: Tweet {tweet_id} -> File not found: {local_path}"
                    )
                    incorrect += 1
                    continue

                # Extract tweet ID from filename
                filename = Path(local_path).name
                match = re.search(r"^(\d+)_\d+\.(mp4|webm)$", filename)
                if match:
                    file_tweet_id = match.group(1)
                    if file_tweet_id == tweet_id:
                        correct += 1
                    else:
                        logger.error(
                            f"✗ MISMATCH: DB tweet_id={tweet_id} but filename has {file_tweet_id}"
                        )
                        incorrect += 1
                else:
                    logger.warning(
                        f"⚠ Tweet {tweet_id}: Filename not in new format: {filename}"
                    )
                    incorrect += 1

            logger.info(f"\nVerification Results:")
            logger.info(f"  ✓ Correct: {correct}")
            logger.info(f"  ✗ Incorrect: {incorrect}")
            logger.info(f"  Total: {correct + incorrect}")

            return correct, incorrect

    def print_summary(self):
        """Print summary of operations."""
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total video files found: {self.stats['total_files']}")
        logger.info(f"Files renamed: {self.stats['renamed']}")
        logger.info(f"Files skipped: {self.stats['skipped']}")
        logger.info(f"Rename errors: {self.stats['errors']}")
        logger.info(f"Database records updated: {self.stats['db_updated']}")
        logger.info(f"Database update errors: {self.stats['db_errors']}")
        logger.info("=" * 60)

    def run(self):
        """Run the complete fix process."""
        logger.info("Starting video mapping fix...")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")

        # Step 1: Scan existing files
        files_by_tweet = self.scan_existing_files()

        if not files_by_tweet:
            logger.error("No video files found!")
            return

        # Step 2: Rename files
        logger.info("\nRenaming video files...")
        rename_map = self.rename_files(files_by_tweet)

        # Step 3: Update database
        if not self.dry_run:
            logger.info("\nUpdating database...")
            self.update_database(rename_map, files_by_tweet)

            # Step 4: Verify
            self.verify_mappings()

        # Print summary
        self.print_summary()

        if self.dry_run:
            logger.info("\n⚠️  This was a DRY RUN. No changes were made.")
            logger.info("Run without --dry-run to apply changes.")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix video file names and database mappings"
    )
    parser.add_argument(
        "--videos-dir",
        default="data/videos",
        help="Path to videos directory (default: data/videos)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    fixer = VideoMappingFixer(videos_dir=args.videos_dir, dry_run=args.dry_run)

    fixer.run()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Download videos for tweets that have API data but missing local_path.
Useful for catching up on videos that weren't downloaded yet.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
import argparse
from database import get_session, Tweet, MediaMetadata, Note

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def find_tweets_with_missing_videos(session, note_status=None):
    """
    Find tweets that have API data but are missing downloaded videos.
    
    Args:
        session: Database session
        note_status: Optional filter for note status (e.g., CURRENTLY_RATED_HELPFUL)
    
    Returns:
        List of tweet IDs
    """
    # Query tweets that:
    # 1. Have API data (raw_api_data is not None)
    # 2. Have notes
    # 3. Have media_metadata indicating videos exist
    # 4. But don't have local_path set (video not downloaded)
    query = (
        session.query(Tweet.tweet_id)
        .join(MediaMetadata, Tweet.tweet_id == MediaMetadata.tweet_id)
        .join(Note, Tweet.tweet_id == Note.tweet_id)
        .filter(Tweet.raw_api_data.isnot(None))
        .filter(MediaMetadata.media_type == "video")
        .filter(MediaMetadata.local_path.is_(None))
        .distinct()
    )
    
    # Optionally filter by note status
    if note_status:
        query = query.filter(Note.current_status == note_status)
    
    tweet_ids = [row.tweet_id for row in query.all()]
    return tweet_ids


def main():
    parser = argparse.ArgumentParser(
        description="Download videos for tweets with API data but missing local_path"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of videos to download (default: all)",
    )
    parser.add_argument(
        "--note-status",
        type=str,
        default=None,
        help="Filter by note status (e.g., CURRENTLY_RATED_HELPFUL)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if video exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("DOWNLOAD MISSING VIDEOS")
    logger.info("=" * 70)
    
    # Find tweets with missing videos
    with get_session() as session:
        logger.info("Searching for tweets with API data but missing videos...")
        if args.note_status:
            logger.info(f"Filtering by note status: {args.note_status}")
        
        tweet_ids = find_tweets_with_missing_videos(session, args.note_status)
        
        if not tweet_ids:
            logger.info("No tweets found with missing videos!")
            return 0
        
        logger.info(f"Found {len(tweet_ids)} tweets with missing videos")
        
        if args.limit and len(tweet_ids) > args.limit:
            logger.info(f"Limiting to first {args.limit} tweets")
            tweet_ids = tweet_ids[:args.limit]
        
        if args.dry_run:
            logger.info("\nDRY RUN - Would download videos for these tweets:")
            for i, tweet_id in enumerate(tweet_ids[:20], 1):
                logger.info(f"  {i}. Tweet ID: {tweet_id}")
            if len(tweet_ids) > 20:
                logger.info(f"  ... and {len(tweet_ids) - 20} more")
            logger.info(f"\nTotal: {len(tweet_ids)} tweets")
            return 0
    
    # Write tweet IDs to temporary file
    temp_file = Path("data/temp_missing_videos.txt")
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(temp_file, "w") as f:
        for tweet_id in tweet_ids:
            f.write(f"{tweet_id}\n")
    
    logger.info(f"Saved tweet IDs to {temp_file}")
    
    # Call download_videos.py with the tweet IDs
    import subprocess
    
    cmd = [
        sys.executable,
        "scripts/data_processing/download_videos.py",
        "--tweet-ids-file",
        str(temp_file),
    ]
    
    if args.limit:
        cmd.extend(["--limit", str(args.limit)])
    
    if args.force:
        cmd.append("--force")
    
    logger.info("\nStarting video download...")
    logger.info("=" * 70)
    
    try:
        result = subprocess.run(cmd, check=True)
        logger.info("\n" + "=" * 70)
        logger.info("✓ Video download completed successfully")
        logger.info("=" * 70)
        return 0
    except subprocess.CalledProcessError as e:
        logger.error(f"\n✗ Video download failed with error code {e.returncode}")
        return 1
    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
            logger.info(f"Cleaned up temporary file: {temp_file}")


if __name__ == "__main__":
    sys.exit(main())

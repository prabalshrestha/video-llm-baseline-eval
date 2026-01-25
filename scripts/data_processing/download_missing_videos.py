#!/usr/bin/env python3
"""
Download videos for tweets that have API data but are missing videos or media_metadata.
Useful for catching up on videos that weren't downloaded yet.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
import argparse
from sqlalchemy.orm import Session
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


def find_tweets_without_media_metadata(session, note_status=None):
    """
    Find tweets that have API data and notes but no media_metadata entries.

    Args:
        session: Database session
        note_status: Optional filter for note status

    Returns:
        List of tweet IDs
    """
    from sqlalchemy import and_, exists

    # Subquery to check if tweet has any media_metadata
    has_media_metadata = exists().where(MediaMetadata.tweet_id == Tweet.tweet_id)

    # Query tweets that:
    # 1. Have API data
    # 2. Have notes
    # 3. Do NOT have any media_metadata entries
    query = (
        session.query(Tweet.tweet_id)
        .join(Note, Tweet.tweet_id == Note.tweet_id)
        .filter(Tweet.raw_api_data.isnot(None))
        .filter(~has_media_metadata)
        .distinct()
    )

    if note_status:
        query = query.filter(Note.current_status == note_status)

    tweet_ids = [row.tweet_id for row in query.all()]
    return tweet_ids


def extract_video_info_from_api_data(session: Session, tweet_ids: list) -> int:
    """
    Extract video information from raw_api_data and create media_metadata entries.

    Args:
        session: Database session
        tweet_ids: List of tweet IDs to process

    Returns:
        Number of media_metadata entries created
    """
    created_count = 0

    for tweet_id in tweet_ids:
        tweet = session.query(Tweet).filter(Tweet.tweet_id == tweet_id).first()

        if not tweet or not tweet.raw_api_data:
            continue

        api_data = tweet.raw_api_data

        # Check if tweet has video attachments
        if "attachments" not in api_data:
            continue

        media_keys = api_data["attachments"].get("media_keys", [])
        if not media_keys:
            continue

        # Get includes.media information
        includes = api_data.get("includes", {})
        media_list = includes.get("media", [])

        if not media_list:
            continue

        # Process each media item
        for video_index, media in enumerate(media_list, 1):
            if media.get("type") != "video":
                continue

            media_key_from_api = media.get("media_key")

            # Create composite media_key
            media_key = f"{tweet_id}_{video_index}"

            # Check if media_metadata already exists
            existing = (
                session.query(MediaMetadata)
                .filter(
                    MediaMetadata.tweet_id == tweet_id,
                    MediaMetadata.video_index == video_index,
                )
                .first()
            )

            if existing:
                continue

            # Create new media_metadata entry
            media_metadata = MediaMetadata(
                media_key=media_key,
                tweet_id=tweet_id,
                video_index=video_index,
                media_type="video",
                media_url=media.get("url"),
                duration_ms=media.get("duration_ms"),
                height=media.get("height"),
                width=media.get("width"),
                preview_image_url=media.get("preview_image_url"),
                view_count=media.get("public_metrics", {}).get("view_count"),
                local_path=None,  # Will be set when video is downloaded
            )

            session.add(media_metadata)
            created_count += 1
            logger.info(
                f"Created media_metadata for tweet {tweet_id} (index {video_index})"
            )

    session.commit()
    return created_count


def main():
    parser = argparse.ArgumentParser(
        description="Download videos for tweets with API data but missing media_metadata or local_path"
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
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Only extract media_metadata from API data, don't download videos",
    )
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("DOWNLOAD MISSING VIDEOS & MAP MEDIA METADATA")
    logger.info("=" * 70)

    all_tweet_ids = set()

    with get_session() as session:
        # Step 1: Find tweets without media_metadata
        logger.info(
            "\n[Step 1] Searching for tweets with API data but no media_metadata..."
        )
        if args.note_status:
            logger.info(f"Filtering by note status: {args.note_status}")

        tweets_no_metadata = find_tweets_without_media_metadata(
            session, args.note_status
        )

        if tweets_no_metadata:
            logger.info(
                f"Found {len(tweets_no_metadata)} tweets without media_metadata"
            )

            if args.dry_run:
                logger.info("\nDRY RUN - Would extract metadata for these tweets:")
                for i, tweet_id in enumerate(tweets_no_metadata[:10], 1):
                    logger.info(f"  {i}. Tweet ID: {tweet_id}")
                if len(tweets_no_metadata) > 10:
                    logger.info(f"  ... and {len(tweets_no_metadata) - 10} more")
            else:
                # Extract media_metadata from API data
                logger.info("\nExtracting video information from API data...")
                created = extract_video_info_from_api_data(session, tweets_no_metadata)
                logger.info(f"✓ Created {created} media_metadata entries")

            all_tweet_ids.update(tweets_no_metadata)
        else:
            logger.info("No tweets found without media_metadata")

        # Step 2: Find tweets with media_metadata but missing local_path
        logger.info(
            "\n[Step 2] Searching for tweets with media_metadata but missing videos..."
        )
        tweets_missing_videos = find_tweets_with_missing_videos(
            session, args.note_status
        )

        if tweets_missing_videos:
            logger.info(
                f"Found {len(tweets_missing_videos)} tweets with missing videos"
            )
            all_tweet_ids.update(tweets_missing_videos)
        else:
            logger.info("No tweets found with missing videos")

    # If extract-only mode, stop here
    if args.extract_only:
        logger.info("\n" + "=" * 70)
        logger.info("✓ Metadata extraction completed (--extract-only mode)")
        logger.info("=" * 70)
        return 0

    # Combine all tweet IDs
    all_tweet_ids = list(all_tweet_ids)

    if not all_tweet_ids:
        logger.info("\n" + "=" * 70)
        logger.info("✓ No videos need to be downloaded!")
        logger.info("=" * 70)
        return 0

    logger.info(f"\n[Step 3] Total {len(all_tweet_ids)} tweets need video downloads")

    if args.limit and len(all_tweet_ids) > args.limit:
        logger.info(f"Limiting to first {args.limit} tweets")
        all_tweet_ids = all_tweet_ids[: args.limit]

    if args.dry_run:
        logger.info("\nDRY RUN - Would download videos for these tweets:")
        for i, tweet_id in enumerate(all_tweet_ids[:20], 1):
            logger.info(f"  {i}. Tweet ID: {tweet_id}")
        if len(all_tweet_ids) > 20:
            logger.info(f"  ... and {len(all_tweet_ids) - 20} more")
        logger.info(f"\nTotal: {len(all_tweet_ids)} tweets")
        return 0

    # Write tweet IDs to temporary file
    temp_file = Path("data/temp_missing_videos.txt")
    temp_file.parent.mkdir(parents=True, exist_ok=True)

    with open(temp_file, "w") as f:
        for tweet_id in all_tweet_ids:
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

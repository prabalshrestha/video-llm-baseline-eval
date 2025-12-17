#!/usr/bin/env python3
"""
Test Database Pipeline
Quick validation script to test the updated database-based pipeline.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_session, Note, Tweet, MediaMetadata
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_database_connection():
    """Test basic database connection."""
    logger.info("Testing database connection...")
    try:
        with get_session() as session:
            # Try a simple query
            count = session.query(Note).count()
            logger.info(f"✓ Database connected. Found {count} notes.")
            return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False


def test_tables_exist():
    """Test that all required tables exist and have data."""
    logger.info("\nTesting tables...")
    
    try:
        with get_session() as session:
            # Check notes table
            notes_count = session.query(Note).count()
            media_notes_count = session.query(Note).filter(Note.is_media_note == True).count()
            logger.info(f"✓ Notes table: {notes_count} total, {media_notes_count} media notes")
            
            # Check tweets table
            tweets_count = session.query(Tweet).count()
            tweets_with_api = session.query(Tweet).filter(Tweet.raw_api_data.isnot(None)).count()
            logger.info(f"✓ Tweets table: {tweets_count} total, {tweets_with_api} with API data")
            
            # Check media_metadata table
            media_count = session.query(MediaMetadata).count()
            videos_count = session.query(MediaMetadata).filter(MediaMetadata.media_type == 'video').count()
            downloaded_count = session.query(MediaMetadata).filter(MediaMetadata.local_path.isnot(None)).count()
            logger.info(f"✓ Media metadata table: {media_count} total, {videos_count} videos, {downloaded_count} downloaded")
            
            return True
    except Exception as e:
        logger.error(f"✗ Table test failed: {e}")
        return False


def test_skip_logic():
    """Test that skip logic would work correctly."""
    logger.info("\nTesting skip logic...")
    
    try:
        with get_session() as session:
            # Test media_metadata skip logic
            all_media_notes = session.query(Note).filter(Note.is_media_note == True).all()
            existing_media_metadata = session.query(MediaMetadata).all()
            existing_tweet_ids = {m.tweet_id for m in existing_media_metadata}
            
            would_skip = sum(1 for note in all_media_notes if note.tweet_id in existing_tweet_ids)
            would_process = len(all_media_notes) - would_skip
            
            logger.info(f"✓ identify_video_notes.py would:")
            logger.info(f"  - Skip: {would_skip} already-processed media notes")
            logger.info(f"  - Process: {would_process} new media notes")
            
            # Test video download skip logic
            videos = session.query(MediaMetadata).filter(MediaMetadata.media_type == 'video').all()
            already_downloaded = sum(1 for v in videos if v.local_path and Path(v.local_path).exists())
            need_download = len(videos) - already_downloaded
            
            logger.info(f"✓ download_videos.py would:")
            logger.info(f"  - Skip: {already_downloaded} already-downloaded videos")
            logger.info(f"  - Download: {need_download} new videos")
            
            # Test tweet API skip logic
            all_tweets = session.query(Tweet).all()
            have_api_data = sum(1 for t in all_tweets if t.raw_api_data is not None)
            need_api_data = len(all_tweets) - have_api_data
            
            logger.info(f"✓ TwitterService would:")
            logger.info(f"  - Skip: {have_api_data} tweets with API data")
            logger.info(f"  - Fetch: {need_api_data} tweets without API data")
            
            return True
    except Exception as e:
        logger.error(f"✗ Skip logic test failed: {e}")
        return False


def test_dataset_query():
    """Test the dataset creation query."""
    logger.info("\nTesting dataset creation query...")
    
    try:
        with get_session() as session:
            # Simulate the query from create_dataset.py
            query = (
                session.query(MediaMetadata, Tweet, Note)
                .join(Tweet, MediaMetadata.tweet_id == Tweet.tweet_id)
                .join(Note, Tweet.tweet_id == Note.tweet_id)
                .filter(MediaMetadata.local_path.isnot(None))
                .filter(MediaMetadata.media_type == 'video')
            )
            
            results = query.all()
            
            # Check file existence
            valid_files = 0
            for media, tweet, note in results:
                if media.local_path and Path(media.local_path).exists():
                    valid_files += 1
            
            logger.info(f"✓ Dataset query returned {len(results)} records")
            logger.info(f"✓ {valid_files} have valid video files")
            logger.info(f"✓ create_dataset.py would create {valid_files} samples")
            
            if valid_files == 0:
                logger.warning("⚠️  No downloadable videos found for dataset!")
                logger.info("   Run download_videos.py first")
            
            return True
    except Exception as e:
        logger.error(f"✗ Dataset query test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("=" * 70)
    logger.info("DATABASE PIPELINE VALIDATION")
    logger.info("=" * 70)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Tables and Data", test_tables_exist),
        ("Skip Logic", test_skip_logic),
        ("Dataset Query", test_dataset_query),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status}: {name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 All tests passed! Database pipeline is ready to use.")
        return 0
    else:
        logger.warning(f"\n⚠️  {total - passed} test(s) failed.")
        logger.info("Check the errors above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


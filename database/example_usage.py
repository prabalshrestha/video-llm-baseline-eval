"""
Example usage of the database module.

This script demonstrates common database operations.
"""

import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_queries():
    """Example: Basic database queries."""
    from database import get_session, Note, Tweet, MediaMetadata
    
    logger.info("=" * 60)
    logger.info("Example 1: Basic Queries")
    logger.info("=" * 60)
    
    with get_session() as session:
        # Get total counts
        note_count = session.query(Note).count()
        tweet_count = session.query(Tweet).count()
        media_count = session.query(MediaMetadata).count()
        
        logger.info(f"Total notes: {note_count}")
        logger.info(f"Total tweets: {tweet_count}")
        logger.info(f"Total media: {media_count}")
        
        # Get a few notes
        notes = session.query(Note).limit(5).all()
        logger.info(f"\nFirst 5 notes:")
        for note in notes:
            logger.info(f"  - Note {note.note_id}: {note.classification}")


def example_filtered_queries():
    """Example: Filtered queries."""
    from database import get_session, Note, Tweet
    
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Filtered Queries")
    logger.info("=" * 60)
    
    with get_session() as session:
        # Get misleading notes
        misleading_notes = (
            session.query(Note)
            .filter(Note.classification == 'MISINFORMED_OR_POTENTIALLY_MISLEADING')
            .limit(10)
            .all()
        )
        
        logger.info(f"Found {len(misleading_notes)} misleading notes")
        
        # Get tweets with high engagement
        popular_tweets = (
            session.query(Tweet)
            .filter(Tweet.likes > 10000)
            .order_by(Tweet.likes.desc())
            .limit(5)
            .all()
        )
        
        logger.info(f"\nTop 5 most liked tweets:")
        for tweet in popular_tweets:
            logger.info(f"  - Tweet {tweet.tweet_id}: {tweet.likes} likes")


def example_joins():
    """Example: Joining tables."""
    from database import get_session, Note, Tweet, MediaMetadata
    
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: Joining Tables")
    logger.info("=" * 60)
    
    with get_session() as session:
        # Join notes and tweets
        results = (
            session.query(Note, Tweet)
            .join(Tweet, Note.tweet_id == Tweet.tweet_id)
            .filter(Note.is_media_note == True)
            .limit(5)
            .all()
        )
        
        logger.info("Notes with tweet information:")
        for note, tweet in results:
            logger.info(f"  - Note {note.note_id} on tweet by @{tweet.author_username}")
        
        # Join all three tables
        full_results = (
            session.query(Note, Tweet, MediaMetadata)
            .join(Tweet, Note.tweet_id == Tweet.tweet_id)
            .join(MediaMetadata, Tweet.tweet_id == MediaMetadata.tweet_id)
            .limit(3)
            .all()
        )
        
        logger.info("\nFull records (note + tweet + media):")
        for note, tweet, media in full_results:
            logger.info(f"  - {media.media_type}: {media.title}")
            logger.info(f"    Classification: {note.classification}")
            logger.info(f"    Engagement: {tweet.likes} likes")


def example_helper_functions():
    """Example: Using query helper functions."""
    from database import get_session
    from database.queries import (
        get_misleading_media,
        get_engagement_stats,
        get_evaluation_dataset
    )
    
    logger.info("\n" + "=" * 60)
    logger.info("Example 4: Helper Functions")
    logger.info("=" * 60)
    
    with get_session() as session:
        # Get engagement statistics
        stats = get_engagement_stats(session)
        logger.info("Engagement Statistics:")
        logger.info(f"  Total tweets: {stats['total_tweets']}")
        logger.info(f"  Average likes: {stats['avg_likes']:.2f}")
        logger.info(f"  Misleading count: {stats['misleading_count']}")
        
        # Get misleading media
        misleading = get_misleading_media(
            session,
            min_engagement=1000,
            media_type='video'
        )
        logger.info(f"\nMisleading videos with >1000 likes: {len(misleading)}")
        
        # Get evaluation dataset
        dataset = get_evaluation_dataset(session, limit=5)
        logger.info(f"\nEvaluation dataset sample:")
        for item in dataset:
            logger.info(f"  - {item['tweet_id']}: {item['classification']}")


def example_jsonb_queries():
    """Example: Querying JSONB columns."""
    from database import get_session, Tweet, MediaMetadata
    from sqlalchemy import func
    
    logger.info("\n" + "=" * 60)
    logger.info("Example 5: JSONB Queries")
    logger.info("=" * 60)
    
    with get_session() as session:
        # Query tweets with API data
        tweets_with_api = (
            session.query(Tweet)
            .filter(Tweet.raw_api_data.isnot(None))
            .limit(3)
            .all()
        )
        
        logger.info("Tweets with API data:")
        for tweet in tweets_with_api:
            logger.info(f"  - Tweet {tweet.tweet_id}")
            if tweet.raw_api_data:
                # Access JSONB fields
                logger.info(f"    Raw data keys: {list(tweet.raw_api_data.keys())}")
        
        # Query media with formats
        media_with_formats = (
            session.query(MediaMetadata)
            .filter(MediaMetadata.formats.isnot(None))
            .limit(3)
            .all()
        )
        
        logger.info("\nMedia with format data:")
        for media in media_with_formats:
            if media.formats and isinstance(media.formats, list):
                logger.info(f"  - Media {media.tweet_id}: {len(media.formats)} formats")


def example_aggregations():
    """Example: Aggregate queries."""
    from database import get_session, Note, Tweet
    from sqlalchemy import func
    
    logger.info("\n" + "=" * 60)
    logger.info("Example 6: Aggregations")
    logger.info("=" * 60)
    
    with get_session() as session:
        # Count by classification
        classification_counts = (
            session.query(
                Note.classification,
                func.count(Note.note_id).label('count')
            )
            .group_by(Note.classification)
            .all()
        )
        
        logger.info("Notes by classification:")
        for classification, count in classification_counts:
            logger.info(f"  - {classification}: {count}")
        
        # Average engagement by media type
        engagement_by_media = (
            session.query(
                Tweet.media_type,
                func.avg(Tweet.likes).label('avg_likes'),
                func.count(Tweet.tweet_id).label('count')
            )
            .filter(Tweet.media_type.isnot(None))
            .group_by(Tweet.media_type)
            .all()
        )
        
        logger.info("\nAverage engagement by media type:")
        for media_type, avg_likes, count in engagement_by_media:
            logger.info(f"  - {media_type}: {avg_likes:.2f} likes (n={count})")


def main():
    """Run all examples."""
    logger.info("Database Usage Examples")
    logger.info("=" * 60)
    
    try:
        example_basic_queries()
        example_filtered_queries()
        example_joins()
        example_helper_functions()
        example_jsonb_queries()
        example_aggregations()
        
        logger.info("\n" + "=" * 60)
        logger.info("All examples completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error running examples: {e}")
        logger.error("Make sure the database is set up and has data.")
        logger.error("Run: python setup_database.py --import-all")


if __name__ == "__main__":
    main()


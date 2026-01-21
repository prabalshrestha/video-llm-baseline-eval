#!/usr/bin/env python3
"""
Re-fetch tweets that have raw_api_data but are missing the 'lang' field.

This script identifies tweets that were fetched before the lang field was added
to the API request, and re-fetches them to populate the lang field.

Usage:
    python3 scripts/data_processing/refetch_tweets_for_lang.py
    python3 scripts/data_processing/refetch_tweets_for_lang.py --batch-size 100
    python3 scripts/data_processing/refetch_tweets_for_lang.py --dry-run
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import get_session, Tweet
from scripts.services.twitter_service import TwitterService
from sqlalchemy import func, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def find_tweets_missing_lang(session) -> list[str]:
    """
    Find tweets that have raw_api_data but are missing the 'lang' field.
    
    Args:
        session: Database session
        
    Returns:
        List of tweet IDs (as strings) that need to be re-fetched
    """
    logger.info("Searching for tweets missing 'lang' field...")
    
    # Query tweets that have raw_api_data but don't have 'lang' key in the JSON
    # Using PostgreSQL JSONB operators: ? checks if key exists
    tweets = session.query(Tweet.tweet_id).filter(
        Tweet.raw_api_data.isnot(None),
        ~Tweet.raw_api_data.has_key('lang')  # SQLAlchemy JSONB has_key method
    ).all()
    
    tweet_ids = [str(t[0]) for t in tweets]
    
    logger.info(f"Found {len(tweet_ids)} tweets missing 'lang' field")
    
    return tweet_ids


def refetch_tweets(tweet_ids: list[str], batch_size: int = 100, dry_run: bool = False):
    """
    Re-fetch tweets from Twitter API.
    
    Args:
        tweet_ids: List of tweet IDs to re-fetch
        batch_size: Number of tweets per API request
        dry_run: If True, only show what would be done without making API calls
    """
    if not tweet_ids:
        logger.info("No tweets to re-fetch!")
        return
    
    logger.info(f"Will re-fetch {len(tweet_ids)} tweets")
    
    if dry_run:
        logger.info("DRY RUN - no API calls will be made")
        logger.info(f"Would re-fetch tweets in batches of {batch_size}")
        logger.info(f"Sample tweet IDs: {tweet_ids[:5]}")
        return
    
    # Initialize Twitter service with force mode to re-fetch existing tweets
    twitter_service = TwitterService(force=True)
    
    if not twitter_service.is_available():
        logger.error("Twitter API credentials not available!")
        logger.error("Please set TWITTER_BEARER_TOKEN in your .env file")
        return
    
    # Fetch tweets (this will automatically save to database)
    logger.info("Starting to re-fetch tweets...")
    results = twitter_service.fetch_tweets(
        tweet_ids=tweet_ids,
        batch_size=batch_size,
        save_to_db=True
    )
    
    logger.info(f"✓ Successfully re-fetched {len(results)} tweets")


def verify_updates(session) -> dict:
    """
    Verify that tweets now have the lang field.
    
    Args:
        session: Database session
        
    Returns:
        Dictionary with verification statistics
    """
    logger.info("Verifying updates...")
    
    total_tweets = session.query(func.count(Tweet.tweet_id)).filter(
        Tweet.raw_api_data.isnot(None)
    ).scalar()
    
    tweets_with_lang = session.query(func.count(Tweet.tweet_id)).filter(
        Tweet.raw_api_data.isnot(None),
        Tweet.raw_api_data.has_key('lang')
    ).scalar()
    
    tweets_missing_lang = total_tweets - tweets_with_lang
    
    stats = {
        "total_with_api_data": total_tweets,
        "with_lang": tweets_with_lang,
        "missing_lang": tweets_missing_lang,
        "percentage_complete": (tweets_with_lang / max(total_tweets, 1)) * 100
    }
    
    logger.info(f"Total tweets with API data: {stats['total_with_api_data']:,}")
    logger.info(f"Tweets with lang field: {stats['with_lang']:,}")
    logger.info(f"Tweets missing lang field: {stats['missing_lang']:,}")
    logger.info(f"Completion: {stats['percentage_complete']:.1f}%")
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Re-fetch tweets to populate missing 'lang' field"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of tweets per API request (max 100, default: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making API calls"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify current state without re-fetching"
    )
    
    args = parser.parse_args()
    
    # Validate batch size
    if args.batch_size < 1 or args.batch_size > 100:
        logger.error("Batch size must be between 1 and 100")
        sys.exit(1)
    
    print("=" * 70)
    print("Re-fetch Tweets for 'lang' Field")
    print("=" * 70)
    print()
    
    with get_session() as session:
        # Initial verification
        logger.info("Initial state:")
        stats_before = verify_updates(session)
        print()
        
        if args.verify_only:
            return
        
        if stats_before['missing_lang'] == 0:
            logger.info("✓ All tweets already have 'lang' field!")
            return
        
        # Find tweets missing lang
        tweet_ids = find_tweets_missing_lang(session)
        print()
        
        # Re-fetch tweets
        refetch_tweets(tweet_ids, batch_size=args.batch_size, dry_run=args.dry_run)
        print()
        
        if not args.dry_run:
            # Final verification
            logger.info("Final state:")
            stats_after = verify_updates(session)
            print()
            
            # Show improvement
            improvement = stats_after['with_lang'] - stats_before['with_lang']
            logger.info(f"✓ Updated {improvement:,} tweets with 'lang' field")
    
    print("=" * 70)
    print("✓ Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()


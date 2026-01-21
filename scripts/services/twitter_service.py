#!/usr/bin/env python3
"""
Twitter/X API Service
Centralized place for all Twitter API interactions.

Updated to use database and skip tweets with existing raw_api_data.
"""

import os
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import get_session, Tweet
from database.import_data import import_tweets_from_api_data

load_dotenv()
logger = logging.getLogger(__name__)


class TwitterService:
    """Handles all Twitter API interactions."""

    def __init__(self, force=False):
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.base_url = "https://api.twitter.com/2"
        self.force = force  # Force re-fetch even if raw_api_data exists

    def is_available(self) -> bool:
        """Check if Twitter API credentials are available."""
        return bool(self.bearer_token)

    def filter_existing_tweets(self, tweet_ids: List[str], session) -> List[str]:
        """
        Filter out tweet IDs that already have raw_api_data (unless force mode).

        Args:
            tweet_ids: List of tweet IDs to check
            session: Database session

        Returns:
            List of tweet IDs that need to be fetched
        """
        if self.force:
            logger.info(f"Force mode: Re-fetching all {len(tweet_ids)} tweets")
            return tweet_ids

        # Query tweets that have raw_api_data
        existing_tweets = (
            session.query(Tweet.tweet_id)
            .filter(
                Tweet.tweet_id.in_([int(tid) for tid in tweet_ids]),
                Tweet.raw_api_data.isnot(None),
            )
            .all()
        )

        existing_ids = {str(t[0]) for t in existing_tweets}

        # Deduplicate input tweet IDs and filter out existing
        unique_tweet_ids = list(set(tweet_ids))
        tweets_to_fetch = [tid for tid in unique_tweet_ids if tid not in existing_ids]

        logger.info(f"Unique tweet IDs to check: {len(unique_tweet_ids)}")
        logger.info(f"Already have API data in DB: {len(existing_ids)}")
        logger.info(f"Need to fetch from API: {len(tweets_to_fetch)}")

        return tweets_to_fetch

    def fetch_tweets(
        self, tweet_ids: List[str], batch_size: int = 100, save_to_db: bool = True
    ) -> Dict[str, Dict]:
        """
        Fetch tweet data from Twitter API and optionally save to database.

        Args:
            tweet_ids: List of tweet IDs to fetch
            batch_size: Number of tweets per request (max 100)
            save_to_db: If True, save to database immediately

        Returns:
            Dictionary mapping tweet_id to tweet data
        """
        if not self.is_available():
            logger.warning("Twitter API credentials not available")
            return {}

        try:
            import requests
            import time

            with get_session() as session:
                # Filter out tweets that already have API data (unless force mode)
                tweet_ids = self.filter_existing_tweets(tweet_ids, session)

                if not tweet_ids:
                    logger.info("No new tweets to fetch!")
                    return {}

                tweets_data = {}
                total_batches = (len(tweet_ids) + batch_size - 1) // batch_size

                for i in range(0, len(tweet_ids), batch_size):
                    batch = tweet_ids[i : i + batch_size]
                    batch_num = i // batch_size + 1

                    logger.info(
                        f"Fetching batch {batch_num}/{total_batches} ({len(batch)} tweets)..."
                    )

                    params = {
                        "ids": ",".join(str(tid) for tid in batch),
                        "tweet.fields": "created_at,author_id,public_metrics,text,entities,attachments,lang,referenced_tweets",
                        "user.fields": "name,username,verified",
                        "expansions": "author_id,attachments.media_keys",
                        "media.fields": "type,url,duration_ms,preview_image_url",
                    }

                    headers = {"Authorization": f"Bearer {self.bearer_token}"}
                    response = requests.get(
                        f"{self.base_url}/tweets", params=params, headers=headers
                    )

                    if response.status_code == 200:
                        data = response.json()
                        tweets = data.get("data", [])
                        users = {
                            u["id"]: u
                            for u in data.get("includes", {}).get("users", [])
                        }

                        # Build tweet data for CURRENT batch only
                        batch_tweets_data = {}
                        for tweet in tweets:
                            author = users.get(tweet.get("author_id"), {})
                            metrics = tweet.get("public_metrics", {})

                            tweet_data = {
                                "tweet_id": tweet["id"],
                                "text": tweet.get("text", ""),
                                "created_at": tweet.get("created_at", ""),
                                "author_id": tweet.get("author_id", ""),
                                "author_name": author.get("name", ""),
                                "author_username": author.get("username", ""),
                                "author_verified": author.get("verified", False),
                                "likes": metrics.get("like_count", 0),
                                "retweets": metrics.get("retweet_count", 0),
                                "replies": metrics.get("reply_count", 0),
                                "quotes": metrics.get("quote_count", 0),
                                "lang": tweet.get("lang"),  # Language code
                                "referenced_tweets": tweet.get(
                                    "referenced_tweets"
                                ),  # For identifying retweets/replies
                                "raw_response": data,  # Store full API response
                            }

                            # Add to both global accumulator and current batch
                            tweets_data[tweet["id"]] = tweet_data
                            batch_tweets_data[tweet["id"]] = tweet_data

                        logger.info(f"  ✓ Fetched {len(tweets)} tweets")

                        # Save ONLY current batch to database
                        if save_to_db and batch_tweets_data:
                            import_tweets_from_api_data(session, batch_tweets_data)
                            logger.info(
                                f"  ✓ Saved {len(batch_tweets_data)} tweets to database"
                            )

                    elif response.status_code == 429:
                        logger.warning("Rate limit reached. Waiting 15 minutes...")
                        time.sleep(900)
                        continue
                    else:
                        logger.error(f"API error: {response.status_code}")

                    time.sleep(1)  # Rate limiting

                logger.info(f"Total tweets fetched: {len(tweets_data)}")
                if save_to_db:
                    logger.info("All tweets saved to database")

                return tweets_data

        except ImportError:
            logger.error("requests library not installed: pip install requests")
            return {}
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
            return {}

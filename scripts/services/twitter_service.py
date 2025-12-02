#!/usr/bin/env python3
"""
Twitter/X API Service
Centralized place for all Twitter API interactions.
"""

import os
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class TwitterService:
    """Handles all Twitter API interactions."""

    def __init__(self):
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.base_url = "https://api.twitter.com/2"

    def is_available(self) -> bool:
        """Check if Twitter API credentials are available."""
        return bool(self.bearer_token)

    def fetch_tweets(
        self, tweet_ids: List[str], batch_size: int = 100
    ) -> Dict[str, Dict]:
        """
        Fetch tweet data from Twitter API.

        Args:
            tweet_ids: List of tweet IDs to fetch
            batch_size: Number of tweets per request (max 100)

        Returns:
            Dictionary mapping tweet_id to tweet data
        """
        if not self.is_available():
            logger.warning("Twitter API credentials not available")
            return {}

        try:
            import requests
            import time

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
                    "tweet.fields": "created_at,author_id,public_metrics,text,entities,attachments",
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
                        u["id"]: u for u in data.get("includes", {}).get("users", [])
                    }

                    for tweet in tweets:
                        author = users.get(tweet.get("author_id"), {})
                        metrics = tweet.get("public_metrics", {})

                        tweets_data[tweet["id"]] = {
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
                        }

                    logger.info(f"  ✓ Fetched {len(tweets)} tweets")

                elif response.status_code == 429:
                    logger.warning("Rate limit reached. Waiting 15 minutes...")
                    time.sleep(900)
                    continue
                else:
                    logger.error(f"API error: {response.status_code}")

                time.sleep(1)  # Rate limiting

            logger.info(f"Total tweets fetched: {len(tweets_data)}")
            return tweets_data

        except ImportError:
            logger.error("requests library not installed: pip install requests")
            return {}
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
            return {}


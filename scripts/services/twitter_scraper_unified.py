#!/usr/bin/env python3
"""
Unified Twitter Scraper with Multiple Fallback Methods
No API limits - uses guest authentication and web scraping.

Methods (in order of preference):
1. Tweepy-Self (guest authentication)
2. SNScrape (CLI-based scraping)
3. Playwright (browser automation)

Installation:
    pip install tweepy-self snscrape playwright
    playwright install chromium
"""

import logging
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import get_session, Tweet
from database.import_data import import_tweets_from_api_data

logger = logging.getLogger(__name__)


class TwitterScraperUnified:
    """
    Unified Twitter scraper with multiple fallback methods.
    No API key required, no rate limits.
    """

    def __init__(self, force=False, method="auto"):
        """
        Initialize scraper.
        
        Args:
            force: Force re-fetch even if data exists
            method: "auto", "tweepy", "snscrape", or "playwright"
        """
        self.force = force
        self.method = method
        self.available_methods = []
        
        # Check which methods are available
        if method == "auto" or method == "tweepy":
            if self._check_tweepy():
                self.available_methods.append("tweepy")
        
        if method == "auto" or method == "snscrape":
            if self._check_snscrape():
                self.available_methods.append("snscrape")
        
        if method == "auto" or method == "playwright":
            if self._check_playwright():
                self.available_methods.append("playwright")
        
        logger.info(f"Available scraping methods: {self.available_methods}")

    def _check_tweepy(self) -> bool:
        """Check if tweepy-self is available."""
        try:
            import tweepy_self
            return True
        except ImportError:
            logger.debug("tweepy-self not available")
            return False

    def _check_snscrape(self) -> bool:
        """Check if snscrape is available."""
        try:
            result = subprocess.run(
                ["snscrape", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.debug("snscrape not available")
            return False

    def _check_playwright(self) -> bool:
        """Check if playwright is available."""
        try:
            import playwright
            return True
        except ImportError:
            logger.debug("playwright not available")
            return False

    def is_available(self) -> bool:
        """Check if any scraping method is available."""
        return len(self.available_methods) > 0

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
        logger.info(f"Need to fetch: {len(tweets_to_fetch)}")

        return tweets_to_fetch

    def fetch_tweets(
        self, tweet_ids: List[str], batch_size: int = 100, save_to_db: bool = True
    ) -> Dict[str, Dict]:
        """
        Fetch tweet data using available scraping methods.
        
        Args:
            tweet_ids: List of tweet IDs to fetch
            batch_size: Number of tweets per batch (for progress tracking)
            save_to_db: If True, save to database immediately
            
        Returns:
            Dictionary mapping tweet_id to tweet data
        """
        if not self.is_available():
            logger.error("No scraping methods available!")
            logger.error("Install at least one: pip install tweepy-self snscrape playwright")
            return {}

        with get_session() as session:
            # Filter out tweets that already have data
            tweet_ids = self.filter_existing_tweets(tweet_ids, session)

            if not tweet_ids:
                logger.info("No new tweets to fetch!")
                return {}

            tweets_data = {}

            # Try each available method
            for method in self.available_methods:
                if method == "tweepy":
                    tweets_data = self._fetch_with_tweepy(tweet_ids)
                elif method == "snscrape":
                    tweets_data = self._fetch_with_snscrape(tweet_ids)
                elif method == "playwright":
                    tweets_data = self._fetch_with_playwright(tweet_ids)

                if tweets_data:
                    logger.info(f"Successfully fetched {len(tweets_data)} tweets using {method}")
                    break
                else:
                    logger.warning(f"{method} failed, trying next method...")

            # Save to database
            if save_to_db and tweets_data:
                import_tweets_from_api_data(session, tweets_data)
                logger.info(f"✓ Saved {len(tweets_data)} tweets to database")

            return tweets_data

    def _fetch_with_tweepy(self, tweet_ids: List[str]) -> Dict[str, Dict]:
        """Fetch tweets using tweepy-self."""
        logger.info("Using tweepy-self scraper...")
        
        try:
            from tweepy_self import API
            api = API()
            tweets_data = {}

            for i, tweet_id in enumerate(tweet_ids, 1):
                try:
                    logger.info(f"Fetching tweet {i}/{len(tweet_ids)}: {tweet_id}")
                    tweet = api.get_tweet(tweet_id)

                    if tweet:
                        user = tweet.user
                        tweets_data[tweet_id] = {
                            "tweet_id": str(tweet.id),
                            "text": getattr(tweet, 'full_text', None) or getattr(tweet, 'text', ''),
                            "created_at": tweet.created_at.isoformat() if tweet.created_at else '',
                            "author_id": str(user.id),
                            "author_name": user.name,
                            "author_username": user.screen_name,
                            "author_verified": user.verified,
                            "likes": tweet.favorite_count,
                            "retweets": tweet.retweet_count,
                            "replies": getattr(tweet, 'reply_count', 0),
                            "quotes": getattr(tweet, 'quote_count', 0),
                            "lang": tweet.lang,
                            "referenced_tweets": self._extract_referenced_tweets_tweepy(tweet),
                            "raw_response": {"source": "tweepy-self", "data": str(tweet.__dict__)},
                        }
                        logger.info(f"  ✓ Fetched tweet {tweet_id}")

                except Exception as e:
                    logger.error(f"  ✗ Error fetching tweet {tweet_id}: {e}")

            return tweets_data

        except Exception as e:
            logger.error(f"Tweepy-self method failed: {e}")
            return {}

    def _fetch_with_snscrape(self, tweet_ids: List[str]) -> Dict[str, Dict]:
        """Fetch tweets using snscrape."""
        logger.info("Using snscrape...")
        
        tweets_data = {}

        for i, tweet_id in enumerate(tweet_ids, 1):
            try:
                logger.info(f"Fetching tweet {i}/{len(tweet_ids)}: {tweet_id}")
                
                # Build snscrape command
                cmd = [
                    'snscrape',
                    '--jsonl',
                    '--max-results', '1',
                    'twitter-tweet',
                    tweet_id
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0 and result.stdout.strip():
                    tweet = json.loads(result.stdout.strip())
                    
                    tweets_data[tweet_id] = {
                        "tweet_id": str(tweet.get('id', tweet_id)),
                        "text": tweet.get('content', ''),
                        "created_at": tweet.get('date', ''),
                        "author_id": str(tweet.get('user', {}).get('id', '')),
                        "author_name": tweet.get('user', {}).get('displayname', ''),
                        "author_username": tweet.get('user', {}).get('username', ''),
                        "author_verified": tweet.get('user', {}).get('verified', False),
                        "likes": tweet.get('likeCount', 0),
                        "retweets": tweet.get('retweetCount', 0),
                        "replies": tweet.get('replyCount', 0),
                        "quotes": tweet.get('quoteCount', 0),
                        "lang": tweet.get('lang'),
                        "referenced_tweets": self._extract_referenced_tweets_snscrape(tweet),
                        "raw_response": {"source": "snscrape", "data": tweet},
                    }
                    logger.info(f"  ✓ Fetched tweet {tweet_id}")

            except Exception as e:
                logger.error(f"  ✗ Error fetching tweet {tweet_id}: {e}")

        return tweets_data

    def _fetch_with_playwright(self, tweet_ids: List[str]) -> Dict[str, Dict]:
        """Fetch tweets using Playwright browser automation."""
        logger.info("Using Playwright browser automation...")
        logger.warning("This method is slower but more reliable")
        
        try:
            import asyncio
            from playwright.async_api import async_playwright

            async def scrape_tweets():
                tweets_data = {}
                
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context()
                    page = await context.new_page()

                    for i, tweet_id in enumerate(tweet_ids, 1):
                        try:
                            logger.info(f"Scraping tweet {i}/{len(tweet_ids)}: {tweet_id}")
                            url = f"https://twitter.com/i/status/{tweet_id}"
                            await page.goto(url, wait_until='networkidle', timeout=30000)

                            # Wait for tweet to load
                            await page.wait_for_selector('article', timeout=10000)

                            # Extract basic data (simplified version)
                            # You can enhance this with more detailed selectors
                            tweet_text = await page.text_content('article div[lang]')
                            
                            tweets_data[tweet_id] = {
                                "tweet_id": tweet_id,
                                "text": tweet_text or "",
                                "created_at": datetime.now().isoformat(),
                                "author_id": "",
                                "author_name": "",
                                "author_username": "",
                                "author_verified": False,
                                "likes": 0,
                                "retweets": 0,
                                "replies": 0,
                                "quotes": 0,
                                "lang": None,
                                "referenced_tweets": None,
                                "raw_response": {"source": "playwright", "url": url},
                            }
                            logger.info(f"  ✓ Scraped tweet {tweet_id}")

                        except Exception as e:
                            logger.error(f"  ✗ Error scraping tweet {tweet_id}: {e}")

                    await browser.close()

                return tweets_data

            # Run async function
            return asyncio.run(scrape_tweets())

        except Exception as e:
            logger.error(f"Playwright method failed: {e}")
            return {}

    def _extract_referenced_tweets_tweepy(self, tweet) -> Optional[List[Dict]]:
        """Extract referenced tweets from tweepy tweet object."""
        referenced = []
        
        if hasattr(tweet, 'retweeted_status'):
            referenced.append({
                'type': 'retweeted',
                'id': str(tweet.retweeted_status.id)
            })
        
        if hasattr(tweet, 'in_reply_to_status_id') and tweet.in_reply_to_status_id:
            referenced.append({
                'type': 'replied_to',
                'id': str(tweet.in_reply_to_status_id)
            })
            
        if hasattr(tweet, 'quoted_status'):
            referenced.append({
                'type': 'quoted',
                'id': str(tweet.quoted_status.id)
            })
            
        return referenced if referenced else None

    def _extract_referenced_tweets_snscrape(self, tweet: Dict) -> Optional[List[Dict]]:
        """Extract referenced tweets from snscrape data."""
        referenced = []
        
        if tweet.get('retweetedTweet'):
            referenced.append({
                'type': 'retweeted',
                'id': str(tweet['retweetedTweet'].get('id', ''))
            })
        
        if tweet.get('inReplyToTweetId'):
            referenced.append({
                'type': 'replied_to',
                'id': str(tweet['inReplyToTweetId'])
            })
            
        if tweet.get('quotedTweet'):
            referenced.append({
                'type': 'quoted',
                'id': str(tweet['quotedTweet'].get('id', ''))
            })
            
        return referenced if referenced else None


def main():
    """Test the scraper."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test with a sample tweet
    scraper = TwitterScraperUnified()
    
    if not scraper.is_available():
        logger.error("No scraping methods available!")
        logger.info("\nInstall one of the following:")
        logger.info("  pip install tweepy-self")
        logger.info("  pip install snscrape")
        logger.info("  pip install playwright && playwright install chromium")
        return

    # Test tweet IDs (use your actual tweet IDs)
    test_tweet_ids = ["1234567890"]  # Replace with real IDs
    
    logger.info(f"Testing scraper with tweet IDs: {test_tweet_ids}")
    tweets_data = scraper.fetch_tweets(test_tweet_ids, save_to_db=False)
    
    if tweets_data:
        logger.info(f"\n✓ Successfully scraped {len(tweets_data)} tweets!")
        for tweet_id, data in tweets_data.items():
            logger.info(f"\nTweet {tweet_id}:")
            logger.info(f"  Text: {data['text'][:100]}...")
            logger.info(f"  Author: @{data['author_username']}")
    else:
        logger.error("Failed to scrape tweets")


if __name__ == "__main__":
    main()

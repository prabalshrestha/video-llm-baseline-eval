"""
Fetch Tweet Data and Identify Videos
This script uses Twitter API v2 to fetch tweet data and identify which tweets contain videos.
"""

import pandas as pd
import os
from pathlib import Path
import logging
from datetime import datetime
import json
from dotenv import load_dotenv
import time

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class TweetDataFetcher:
    """
    Fetches tweet data using Twitter API v2 to identify which tweets contain videos.
    """

    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.filtered_dir = self.data_dir / "filtered"
        self.videos_dir = self.data_dir / "videos"
        self.videos_dir.mkdir(exist_ok=True)

        # Twitter API credentials
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        if not self.bearer_token:
            logger.error("TWITTER_BEARER_TOKEN not found in environment variables")
            logger.info("Please add it to your .env file")

    def load_media_notes(self, filepath=None):
        """Load filtered media notes."""
        if filepath is None:
            filepath = self.filtered_dir / "media_notes.csv"

        try:
            df = pd.read_csv(filepath)
            logger.info(f"Loaded {len(df)} media notes from {filepath}")
            return df
        except Exception as e:
            logger.error(f"Failed to load media notes: {e}")
            return None

    def extract_unique_tweet_ids(self, df, limit=None):
        """Extract unique tweet IDs from the notes dataframe."""
        if "tweetId" not in df.columns:
            logger.error("tweetId column not found")
            return []

        tweet_ids = df["tweetId"].unique().tolist()

        if limit:
            tweet_ids = tweet_ids[:limit]

        logger.info(f"Extracted {len(tweet_ids)} unique tweet IDs")
        return tweet_ids

    def fetch_tweets_batch(self, tweet_ids, batch_size=100):
        """
        Fetch tweet data using Twitter API v2.

        Args:
            tweet_ids: List of tweet IDs to fetch
            batch_size: Number of tweets to fetch per request (max 100)

        Returns:
            List of tweet data dictionaries
        """
        if not self.bearer_token:
            logger.error("Cannot fetch tweets without Twitter API credentials")
            logger.info(
                "\nTo get Twitter API access:\n"
                "1. Go to https://developer.twitter.com\n"
                "2. Apply for a developer account\n"
                "3. Create a project and app\n"
                "4. Get your Bearer Token\n"
                "5. Add to .env file: TWITTER_BEARER_TOKEN=your_token_here"
            )
            return None

        try:
            import requests

            all_tweets = []
            total_batches = (len(tweet_ids) + batch_size - 1) // batch_size

            for i in range(0, len(tweet_ids), batch_size):
                batch = tweet_ids[i : i + batch_size]
                batch_num = i // batch_size + 1

                logger.info(
                    f"Fetching batch {batch_num}/{total_batches} ({len(batch)} tweets)..."
                )

                # Twitter API v2 endpoint
                url = "https://api.twitter.com/2/tweets"

                # Parameters
                params = {
                    "ids": ",".join(str(tid) for tid in batch),
                    "tweet.fields": "created_at,author_id,public_metrics,entities,attachments",
                    "media.fields": "type,url,duration_ms,preview_image_url,variants",
                    "expansions": "attachments.media_keys",
                }

                headers = {"Authorization": f"Bearer {self.bearer_token}"}

                response = requests.get(url, params=params, headers=headers)

                if response.status_code == 200:
                    data = response.json()

                    # Extract tweets and media
                    tweets = data.get("data", [])
                    media = {m["media_key"]: m for m in data.get("includes", {}).get("media", [])}

                    # Add media info to tweets
                    for tweet in tweets:
                        if "attachments" in tweet and "media_keys" in tweet["attachments"]:
                            tweet["media"] = [
                                media[mk]
                                for mk in tweet["attachments"]["media_keys"]
                                if mk in media
                            ]

                    all_tweets.extend(tweets)
                    logger.info(f"  ✓ Fetched {len(tweets)} tweets")

                elif response.status_code == 429:
                    logger.warning("Rate limit reached. Waiting 15 minutes...")
                    time.sleep(900)  # Wait 15 minutes
                    continue

                else:
                    logger.error(
                        f"API request failed: {response.status_code} - {response.text}"
                    )

                # Rate limiting: wait between requests
                time.sleep(1)

            logger.info(f"Total tweets fetched: {len(all_tweets)}")
            return all_tweets

        except ImportError:
            logger.error("requests library not installed. Run: pip install requests")
            return None
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
            return None

    def filter_video_tweets(self, tweets):
        """Filter tweets that contain video media."""
        video_tweets = []

        for tweet in tweets:
            if "media" in tweet:
                for media_item in tweet["media"]:
                    if media_item.get("type") == "video":
                        video_tweets.append(
                            {
                                "tweet_id": tweet["id"],
                                "text": tweet.get("text", ""),
                                "created_at": tweet.get("created_at", ""),
                                "author_id": tweet.get("author_id", ""),
                                "media_key": media_item.get("media_key", ""),
                                "video_duration_ms": media_item.get("duration_ms", 0),
                                "preview_image_url": media_item.get(
                                    "preview_image_url", ""
                                ),
                                "video_variants": media_item.get("variants", []),
                            }
                        )
                        break  # Only count once per tweet

        logger.info(f"Found {len(video_tweets)} tweets with videos")
        return video_tweets

    def save_video_tweet_data(self, video_tweets, filename="video_tweets.json"):
        """Save video tweet data to file."""
        output_path = self.filtered_dir / filename

        with open(output_path, "w") as f:
            json.dump(video_tweets, f, indent=2)

        logger.info(f"Saved video tweet data to {output_path}")

        # Also save as CSV for easier viewing
        if video_tweets:
            df = pd.DataFrame(video_tweets)
            # Drop complex nested fields for CSV
            df_simple = df.drop(columns=["video_variants"], errors="ignore")
            csv_path = self.filtered_dir / filename.replace(".json", ".csv")
            df_simple.to_csv(csv_path, index=False)
            logger.info(f"Also saved simplified version to {csv_path}")

        return output_path

    def run(self, limit=None):
        """
        Main execution method.

        Args:
            limit: Limit number of tweets to fetch (for testing). None = all tweets.
        """
        logger.info("=" * 70)
        logger.info("TWEET DATA FETCHER - Identifying Video Tweets")
        logger.info("=" * 70)

        # Step 1: Load media notes
        logger.info("\nStep 1: Loading media notes...")
        media_notes = self.load_media_notes()

        if media_notes is None:
            logger.error("Failed to load media notes")
            return None

        # Step 2: Extract tweet IDs
        logger.info("\nStep 2: Extracting tweet IDs...")
        tweet_ids = self.extract_unique_tweet_ids(media_notes, limit=limit)

        if not tweet_ids:
            logger.error("No tweet IDs found")
            return None

        # Step 3: Fetch tweet data
        logger.info(f"\nStep 3: Fetching tweet data for {len(tweet_ids)} tweets...")
        logger.info("This may take a while depending on API rate limits...")

        tweets = self.fetch_tweets_batch(tweet_ids)

        if not tweets:
            logger.error("Failed to fetch tweet data")
            return None

        # Step 4: Filter for videos
        logger.info("\nStep 4: Filtering for tweets with videos...")
        video_tweets = self.filter_video_tweets(tweets)

        if not video_tweets:
            logger.warning("No video tweets found")
            return None

        # Step 5: Save results
        logger.info("\nStep 5: Saving results...")
        output_file = self.save_video_tweet_data(video_tweets)

        # Step 6: Summary
        logger.info("\n" + "=" * 70)
        logger.info("SUCCESS!")
        logger.info("=" * 70)
        logger.info(f"Total media notes: {len(media_notes)}")
        logger.info(f"Unique tweets checked: {len(tweet_ids)}")
        logger.info(f"Tweets with videos: {len(video_tweets)}")
        logger.info(
            f"Video percentage: {len(video_tweets)/len(tweet_ids)*100:.1f}%"
        )
        logger.info(f"\nResults saved to: {output_file}")
        logger.info("\nNext step: Download videos using video URLs")

        return video_tweets


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch tweet data and identify video tweets"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of tweets to fetch (for testing)",
    )
    args = parser.parse_args()

    fetcher = TweetDataFetcher(data_dir="data")
    result = fetcher.run(limit=args.limit)

    if result is not None:
        print("\n✓ Tweet data fetching completed successfully!")
        print("✓ Check data/filtered/ for results")
    else:
        print("\n✗ Failed to fetch tweet data")
        print(
            "Make sure you have Twitter API credentials in .env file"
        )


if __name__ == "__main__":
    main()


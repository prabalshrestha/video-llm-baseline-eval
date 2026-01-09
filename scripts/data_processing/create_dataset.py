#!/usr/bin/env python3
"""
Create Evaluation Dataset
Creates the complete evaluation dataset from database.
Queries notes, tweets, and media_metadata tables to build the final dataset.

Updated to use database instead of CSV files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.twitter_service import TwitterService
from database import get_session, Note, Tweet, MediaMetadata

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatasetCreator:
    """Creates the complete evaluation dataset from database."""

    def __init__(
        self,
        data_dir: str = "data",
        force_api_fetch: bool = False,
        sample_size: int = None,
        random_seed: int = 42,
        api_data_only: bool = False,
    ):
        self.data_dir = Path(data_dir)
        self.output_dir = self.data_dir / "evaluation"
        self.output_dir.mkdir(exist_ok=True)
        self.force_api_fetch = force_api_fetch
        self.sample_size = sample_size  # Number of samples to randomly select
        self.random_seed = random_seed  # For reproducible sampling
        self.api_data_only = api_data_only  # Only include tweets with existing API data

        self.twitter = TwitterService(force=force_api_fetch)

    def load_data_from_database(self, session) -> List[Dict]:
        """
        Load all data from database for videos with local_path set.

        Returns:
            List of dictionaries with joined data from notes, tweets, and media_metadata
        """
        # Query videos that have been downloaded (local_path is set)
        query = (
            session.query(MediaMetadata, Tweet, Note)
            .join(Tweet, MediaMetadata.tweet_id == Tweet.tweet_id)
            .join(Note, Tweet.tweet_id == Note.tweet_id)
            .filter(MediaMetadata.local_path.isnot(None))
            .filter(MediaMetadata.media_type == "video")
        )
        
        # Filter for tweets with API data if requested
        if self.api_data_only:
            query = query.filter(Tweet.raw_api_data.isnot(None))

        results = query.all()
        logger.info(f"Found {len(results)} downloaded videos with notes in database")
        if self.api_data_only:
            logger.info("  ✓ Filtered to only tweets with API data")

        # Convert to list of dicts for easier processing
        data = []
        for media, tweet, note in results:
            # Check if file actually exists
            if media.local_path and not Path(media.local_path).exists():
                logger.warning(f"Video file not found: {media.local_path}")
                continue

            data.append(
                {
                    "media": media,
                    "tweet": tweet,
                    "note": note,
                }
            )

        logger.info(f"Loaded {len(data)} complete records (with existing video files)")

        # Apply random sampling if requested
        if self.sample_size and self.sample_size < len(data):
            import random

            random.seed(self.random_seed)
            data = random.sample(data, self.sample_size)
            logger.info(
                f"✓ Randomly sampled {self.sample_size} videos (seed={self.random_seed})"
            )

        return data

    def fetch_missing_tweet_data(self, session, data: List[Dict]) -> int:
        """
        Fetch tweet API data for tweets that don't have it yet.

        Args:
            session: Database session
            data: List of data dicts from load_data_from_database

        Returns:
            Number of tweets fetched
        """
        # Find tweet IDs without raw_api_data (deduplicate since same tweet can appear multiple times)
        tweets_without_api = list(
            set(
                [
                    str(d["tweet"].tweet_id)
                    for d in data
                    if d["tweet"].raw_api_data is None
                ]
            )
        )

        if not tweets_without_api:
            logger.info("All tweets already have API data")
            return 0

        logger.info(
            f"Found {len(tweets_without_api)} unique tweets without API data (from {sum(1 for d in data if d['tweet'].raw_api_data is None)} records)"
        )

        if not self.twitter.is_available():
            logger.warning("Twitter API not available - skipping API fetch")
            return 0

        logger.info("Fetching missing tweet data from Twitter API...")
        self.twitter.fetch_tweets(tweets_without_api, save_to_db=True)

        # Refresh the session to get updated data
        session.expire_all()

        return len(tweets_without_api)

    def create_dataset(self, data: List[Dict]) -> List[Dict]:
        """
        Create the complete dataset from database records.

        Args:
            data: List of dicts with 'media', 'tweet', 'note' keys

        Returns:
            List of dataset entries
        """
        dataset = []

        for idx, record in enumerate(data, 1):
            media = record["media"]
            tweet = record["tweet"]
            note = record["note"]

            # Get filename from local_path
            video_path = Path(media.local_path) if media.local_path else None
            filename = video_path.name if video_path else f"video_{idx:03d}"

            # Convert duration from ms to seconds
            duration_seconds = media.duration_ms / 1000.0 if media.duration_ms else 0

            # Build entry
            entry = {
                "video": {
                    "filename": filename,
                    "index": idx,
                    "duration_seconds": duration_seconds,
                    "path": str(video_path) if video_path else "",
                    "title": media.title or "",
                    "uploader": media.uploader or "",
                    "width": media.width,
                    "height": media.height,
                },
                "tweet": {
                    "tweet_id": str(tweet.tweet_id),
                    "url": tweet.tweet_url
                    or f"https://twitter.com/i/status/{tweet.tweet_id}",
                    "text": tweet.text or "",
                    "author_name": tweet.author_name or "",
                    "author_username": tweet.author_username or "",
                    "author_verified": tweet.author_verified or False,
                    "created_at": (
                        tweet.created_at.isoformat() if tweet.created_at else ""
                    ),
                    "engagement": {
                        "likes": tweet.likes or 0,
                        "retweets": tweet.retweets or 0,
                        "replies": tweet.replies or 0,
                        "quotes": tweet.quotes or 0,
                    },
                },
                "community_note": {
                    "note_id": str(note.note_id),
                    "note_url": note.note_url
                    or f"https://twitter.com/i/birdwatch/n/{note.note_id}",
                    "classification": note.classification or "",
                    "summary": note.summary or "",
                    "is_misleading": note.classification
                    == "MISINFORMED_OR_POTENTIALLY_MISLEADING",
                    "created_at_millis": note.created_at_millis,
                    "reasons": {
                        "factual_error": note.misleading_factual_error or 0,
                        "manipulated_media": note.misleading_manipulated_media or 0,
                        "missing_context": note.misleading_missing_important_context
                        or 0,
                        "outdated_info": note.misleading_outdated_information or 0,
                        "unverified_claim": note.misleading_unverified_claim_as_fact
                        or 0,
                        "satire": note.misleading_satire or 0,
                    },
                    "not_misleading_reasons": {
                        "factually_correct": note.not_misleading_factually_correct or 0,
                        "clearly_satire": note.not_misleading_clearly_satire or 0,
                        "personal_opinion": note.not_misleading_personal_opinion or 0,
                    },
                    "believable": note.believable,
                    "harmful": note.harmful,
                    "validation_difficulty": note.validation_difficulty,
                },
                "metadata": {
                    "sample_id": f"video_{idx:03d}",
                    "has_api_data": tweet.raw_api_data is not None,
                    "created_at": datetime.now().isoformat(),
                    "media_type": media.media_type,
                },
            }

            dataset.append(entry)

        return dataset

    def save_dataset(self, dataset: List[Dict]):
        """Save dataset in multiple formats."""
        # Main JSON file
        output = {
            "dataset_info": {
                "name": "Video LLM Misinformation Evaluation Dataset",
                "description": "Videos with tweets and community notes for misinformation detection",
                "version": "2.0",
                "created": datetime.now().isoformat(),
                "total_samples": len(dataset),
            },
            "statistics": {
                "total": len(dataset),
                "misleading": sum(
                    1 for d in dataset if d["community_note"]["is_misleading"]
                ),
                "with_api_data": sum(
                    1 for d in dataset if d["metadata"]["has_api_data"]
                ),
                "total_duration": sum(d["video"]["duration_seconds"] for d in dataset),
            },
            "samples": dataset,
        }

        # Save JSON
        json_file = self.output_dir / "dataset.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        logger.info(f"✓ Saved: {json_file}")

        # Save CSV (flattened)
        try:
            import pandas as pd

            flattened = []
            for entry in dataset:
                flat = {
                    "sample_id": entry["metadata"]["sample_id"],
                    "video_filename": entry["video"]["filename"],
                    "video_duration": entry["video"]["duration_seconds"],
                    "tweet_id": entry["tweet"]["tweet_id"],
                    "tweet_url": entry["tweet"]["url"],
                    "tweet_text": entry["tweet"]["text"],
                    "tweet_author": entry["tweet"]["author_username"],
                    "tweet_likes": entry["tweet"]["engagement"]["likes"],
                    "note_classification": entry["community_note"]["classification"],
                    "note_summary": entry["community_note"]["summary"],
                    "is_misleading": entry["community_note"]["is_misleading"],
                    "has_api_data": entry["metadata"]["has_api_data"],
                }
                flattened.append(flat)

            csv_file = self.output_dir / "dataset.csv"
            df = pd.DataFrame(flattened)
            df.to_csv(csv_file, index=False, encoding="utf-8")
            logger.info(f"✓ Saved: {csv_file}")
        except Exception as e:
            logger.warning(f"Could not save CSV: {e}")

    def run(self, use_api: bool = True) -> bool:
        """
        Create the complete dataset from database.

        Args:
            use_api: Whether to fetch missing tweet API data

        Returns:
            Success status
        """
        logger.info("=" * 70)
        logger.info("CREATING EVALUATION DATASET FROM DATABASE")
        logger.info("=" * 70)

        try:
            with get_session() as session:
                # Load all data from database
                logger.info("\n📂 Loading data from database...")
                data = self.load_data_from_database(session)

                if not data:
                    logger.error("No downloaded videos found in database!")
                    logger.info("\n💡 Make sure you have:")
                    logger.info("   1. Imported notes to database")
                    logger.info("   2. Identified video notes (media_metadata)")
                    logger.info("   3. Downloaded videos (local_path set)")
                    return False

                # Fetch missing tweet API data if requested
                if use_api:
                    logger.info("\n🔑 Checking for missing tweet API data...")
                    fetched = self.fetch_missing_tweet_data(session, data)
                    if fetched > 0:
                        logger.info(f"Fetched API data for {fetched} tweets")
                        # Reload data to get updated tweet info
                        data = self.load_data_from_database(session)

                # Create dataset
                logger.info("\n🔨 Creating dataset...")
                dataset = self.create_dataset(data)
                logger.info(f"Created {len(dataset)} samples")

                # Save
                logger.info("\n💾 Saving dataset...")
                self.save_dataset(dataset)

                # Summary
                logger.info("\n" + "=" * 70)
                logger.info("✅ SUCCESS!")
                logger.info("=" * 70)
                logger.info(f"Total samples: {len(dataset)}")
                unique_tweets = len(set(d['tweet']['tweet_id'] for d in dataset))
                logger.info(f"Unique tweets: {unique_tweets}")
                logger.info(
                    f"With API data: {sum(1 for d in dataset if d['metadata']['has_api_data'])}"
                )
                logger.info(
                    f"Misleading: {sum(1 for d in dataset if d['community_note']['is_misleading'])}"
                )
                logger.info(f"\nOutput: {self.output_dir}/dataset.json")
                logger.info(f"        {self.output_dir}/dataset.csv")

                missing_api = sum(
                    1 for d in dataset if not d["metadata"]["has_api_data"]
                )
                if missing_api > 0:
                    logger.info(
                        f"\n💡 {missing_api} samples don't have Twitter API data"
                    )
                    if not use_api:
                        logger.info("   Run with --use-api to fetch missing data")
                    elif not self.twitter.is_available():
                        logger.info(
                            "   Add TWITTER_BEARER_TOKEN to .env to fetch API data"
                        )

                return True

        except Exception as e:
            logger.error(f"Failed to create dataset: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create evaluation dataset from database"
    )
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="Don't use Twitter API even if available",
    )
    parser.add_argument(
        "--force-api-fetch",
        action="store_true",
        help="Force re-fetch all tweet data from API, even if already in database",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Randomly sample N videos for diversity (e.g., --sample-size 100)",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42)",
    )
    parser.add_argument(
        "--api-data-only",
        action="store_true",
        help="Only include tweets that already have API data (no fetching needed)",
    )
    args = parser.parse_args()

    creator = DatasetCreator(
        force_api_fetch=args.force_api_fetch,
        sample_size=args.sample_size,
        random_seed=args.random_seed,
        api_data_only=args.api_data_only,
    )
    success = creator.run(use_api=not args.no_api)

    if success:
        print("\n✅ Dataset created successfully from database!")
        print("📁 Check data/evaluation/dataset.json")
        print("📁 Check data/evaluation/dataset.csv")
    else:
        print("\n❌ Failed to create dataset")
        sys.exit(1)


if __name__ == "__main__":
    main()

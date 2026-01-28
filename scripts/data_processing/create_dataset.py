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
        random_seed: int = None,
        api_data_only: bool = False,
        note_status_filter: str = None,
        tweet_ids: List[str] = None,
    ):
        self.data_dir = Path(data_dir)
        self.output_dir = self.data_dir / "evaluation"
        self.output_dir.mkdir(exist_ok=True)
        self.force_api_fetch = force_api_fetch
        self.sample_size = sample_size  # Number of samples to randomly select
        self.random_seed = (
            random_seed
            if random_seed is not None
            else int(datetime.now().timestamp() * 1000) % 2**32
        )  # For reproducible sampling
        self.api_data_only = api_data_only  # Only include tweets with existing API data
        self.note_status_filter = note_status_filter  # Filter notes by status
        self.tweet_ids = tweet_ids  # Optional: specific tweet IDs to include

        self.twitter = TwitterService(force=force_api_fetch)

    @staticmethod
    def is_original_tweet(tweet: Tweet) -> bool:
        """
        Check if tweet is an original tweet (not a retweet or reply).

        Args:
            tweet: Tweet object with raw_api_data

        Returns:
            True if original tweet, False if retweet or reply
        """
        if not tweet.raw_api_data:
            # If no API data, can't determine - assume original
            return True

        api_data = tweet.raw_api_data

        # Check for referenced_tweets (indicates retweet or reply)
        # The structure can be in different places depending on API response
        referenced_tweets = None

        # Check in root level
        if isinstance(api_data, dict):
            referenced_tweets = api_data.get("referenced_tweets")

            # Also check in 'data' if present (some API responses nest it)
            if not referenced_tweets and "data" in api_data:
                if isinstance(api_data["data"], dict):
                    referenced_tweets = api_data["data"].get("referenced_tweets")

        # If referenced_tweets exists and is not empty, it's not original
        if referenced_tweets and len(referenced_tweets) > 0:
            return False

        return True

    @staticmethod
    def is_english_tweet(tweet: Tweet) -> bool:
        """
        Check if tweet is in English.

        Args:
            tweet: Tweet object with raw_api_data

        Returns:
            True if tweet is in English, False otherwise
        """
        if not tweet.raw_api_data:
            # If no API data, can't determine - assume English
            return True

        api_data = tweet.raw_api_data

        # Check for lang field
        lang = None

        # Check in root level
        if isinstance(api_data, dict):
            lang = api_data.get("lang")

            # Also check in 'data' if present (some API responses nest it)
            if not lang and "data" in api_data:
                if isinstance(api_data["data"], dict):
                    lang = api_data["data"].get("lang")

        # Return True if lang is 'en' or if we can't determine
        return lang == "en" if lang else True

    def load_data_from_database(self, session) -> List[Dict]:
        """
        Load unique tweets from database with their videos and notes.

        NEW: Returns one entry per tweet (not per note) with all notes grouped.
        For tweets with multiple videos, only the first video (video_index=1) is used.

        Returns:
            List of dictionaries with tweet, media, and associated notes
        """
        # Query unique tweets that have:
        # 1. Downloaded videos (local_path is set)
        # 2. At least one note
        # 3. Use only first video (video_index=1) for tweets with multiple videos
        # Note: API data filter removed - now fetched in pipeline step 1.5
        query = (
            session.query(Tweet, MediaMetadata)
            .join(MediaMetadata, Tweet.tweet_id == MediaMetadata.tweet_id)
            .filter(MediaMetadata.local_path.isnot(None))
            .filter(MediaMetadata.media_type == "video")
            .filter(MediaMetadata.video_index == 1)  # Only first video per tweet
        )

        # Filter by specific tweet IDs if provided
        if self.tweet_ids:
            query = query.filter(Tweet.tweet_id.in_(self.tweet_ids))
            logger.info(f"Filtering to {len(self.tweet_ids)} specific tweet IDs")

        tweet_media_pairs = query.all()
        logger.info(f"Found {len(tweet_media_pairs)} tweets with downloaded videos")

        # Filter for original English tweets
        filtered_tweets = []
        stats = {
            "total": len(tweet_media_pairs),
            "not_original": 0,
            "not_english": 0,
            "no_file": 0,
            "no_api_data": 0,
        }

        for tweet, media in tweet_media_pairs:
            # Check if video file exists
            if not Path(media.local_path).exists():
                logger.warning(f"Video file not found: {media.local_path}")
                stats["no_file"] += 1
                continue

            # Skip tweets without API data (will be logged as warning)
            if not tweet.raw_api_data:
                stats["no_api_data"] += 1
                continue

            # Check if original tweet (not retweet or reply)
            if not self.is_original_tweet(tweet):
                stats["not_original"] += 1
                continue

            # Check if English
            if not self.is_english_tweet(tweet):
                stats["not_english"] += 1
                continue

            filtered_tweets.append((tweet, media))

        logger.info(f"After filtering:")
        logger.info(f"  ✓ Original tweets (not RT/reply): {len(filtered_tweets)}")
        logger.info(f"  ✗ Filtered out {stats['not_original']} retweets/replies")
        logger.info(f"  ✗ Filtered out {stats['not_english']} non-English tweets")
        logger.info(f"  ✗ Skipped {stats['no_file']} missing video files")
        if stats["no_api_data"] > 0:
            logger.warning(
                f"  ✗ Skipped {stats['no_api_data']} tweets without API data"
            )

        # Now fetch all notes for these tweets
        tweet_ids = [tweet.tweet_id for tweet, _ in filtered_tweets]

        # Query all notes for these tweets
        notes_query = (
            session.query(Note)
            .filter(Note.tweet_id.in_(tweet_ids))
            .order_by(Note.tweet_id, Note.created_at_millis)
        )

        # Apply note status filter if specified
        if self.note_status_filter:
            notes_query = notes_query.filter(
                Note.current_status == self.note_status_filter
            )
            logger.info(f"Filtering notes by status: {self.note_status_filter}")

        all_notes = notes_query.all()
        logger.info(
            f"Found {len(all_notes)} total notes for {len(filtered_tweets)} tweets"
        )

        # Group notes by tweet_id
        from collections import defaultdict

        notes_by_tweet = defaultdict(list)
        for note in all_notes:
            notes_by_tweet[note.tweet_id].append(note)

        # Build final data structure: one entry per tweet with notes array
        # Only include tweets that have matching notes
        data = []
        skipped_no_matching_notes = 0
        for tweet, media in filtered_tweets:
            notes = notes_by_tweet.get(tweet.tweet_id, [])
            if not notes:
                skipped_no_matching_notes += 1
                continue

            data.append(
                {
                    "tweet": tweet,
                    "media": media,
                    "notes": notes,  # Array of Note objects
                }
            )

        logger.info(
            f"Final dataset: {len(data)} tweets with {len(all_notes)} total notes"
        )
        if skipped_no_matching_notes > 0:
            logger.info(
                f"  ✗ Skipped {skipped_no_matching_notes} tweets with no matching notes"
            )
        if len(data) > 0:
            logger.info(f"  Average notes per tweet: {len(all_notes) / len(data):.2f}")

        # Apply random sampling if requested
        if self.sample_size and self.sample_size < len(data):
            import random

            random.seed(self.random_seed)
            data = random.sample(data, self.sample_size)
            logger.info(
                f"✓ Randomly sampled {self.sample_size} tweets (seed={self.random_seed})"
            )

        return data

    def fetch_missing_tweet_data(self, session, data: List[Dict]) -> int:
        """
        Fetch tweet API data for tweets that don't have it yet.

        NOTE: With new filtering, this should rarely be needed since we require API data.

        Args:
            session: Database session
            data: List of data dicts from load_data_from_database (new structure)

        Returns:
            Number of tweets fetched
        """
        # Find tweet IDs without raw_api_data
        tweets_without_api = [
            str(d["tweet"].tweet_id) for d in data if d["tweet"].raw_api_data is None
        ]

        if not tweets_without_api:
            logger.info("All tweets already have API data")
            return 0

        logger.info(f"Found {len(tweets_without_api)} tweets without API data")

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

        NEW: One record per tweet with array of community notes.

        Args:
            data: List of dicts with 'media', 'tweet', 'notes' keys (notes is array)

        Returns:
            List of dataset entries (one per tweet)
        """
        dataset = []

        for idx, record in enumerate(data, 1):
            media = record["media"]
            tweet = record["tweet"]
            notes = record["notes"]  # Array of Note objects

            # Get filename from local_path
            video_path = Path(media.local_path) if media.local_path else None
            filename = video_path.name if video_path else f"video_{idx:03d}"

            # Convert duration from ms to seconds
            duration_seconds = media.duration_ms / 1000.0 if media.duration_ms else 0

            # Build community notes array
            community_notes = []
            for note in notes:
                note_entry = {
                    "note_id": str(note.note_id),
                    "note_url": note.note_url
                    or f"https://twitter.com/i/birdwatch/n/{note.note_id}",
                    "classification": note.classification or "",
                    "summary": note.summary or "",
                    "is_misleading": note.classification
                    == "MISINFORMED_OR_POTENTIALLY_MISLEADING",
                    "created_at_millis": note.created_at_millis,
                    "current_status": note.current_status or "",  # NEW FIELD
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
                }
                community_notes.append(note_entry)

            # Build entry (one per tweet with notes array)
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
                "community_notes": community_notes,  # Array instead of single object
                "metadata": {
                    "sample_id": f"video_{idx:03d}",
                    "tweet_id": str(tweet.tweet_id),  # NEW: explicit tweet_id
                    "num_notes": len(community_notes),  # NEW: number of notes
                    "has_api_data": tweet.raw_api_data is not None,
                    "is_original_tweet": True,  # All filtered to be original
                    "is_english": True,  # All filtered to be English
                    "created_at": datetime.now().isoformat(),
                    "media_type": media.media_type,
                },
            }

            dataset.append(entry)

        return dataset

    def save_dataset(self, dataset: List[Dict]):
        """Save dataset in multiple formats with timestamp and latest symlink."""
        # Calculate statistics
        total_notes = sum(len(d["community_notes"]) for d in dataset)

        # Count notes by status
        from collections import Counter

        status_counts = Counter()
        for entry in dataset:
            for note in entry["community_notes"]:
                status = note.get("current_status", "UNKNOWN")
                status_counts[status] += 1

        # Count misleading notes
        misleading_notes = sum(
            1 for d in dataset for note in d["community_notes"] if note["is_misleading"]
        )

        # Create timestamp for this dataset
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create datasets directory if it doesn't exist
        datasets_dir = self.output_dir / "datasets"
        datasets_dir.mkdir(parents=True, exist_ok=True)

        # Main JSON file
        output = {
            "dataset_info": {
                "name": "Video LLM Misinformation Evaluation Dataset",
                "description": "Videos with tweets and community notes for misinformation detection (one record per tweet)",
                "version": "3.0",  # Updated version
                "created": datetime.now().isoformat(),
                "timestamp": timestamp,
                "total_tweets": len(dataset),
                "total_notes": total_notes,
                "note_status_filter": self.note_status_filter or "None",
            },
            "statistics": {
                "total_tweets": len(dataset),
                "total_notes": total_notes,
                "avg_notes_per_tweet": total_notes / len(dataset) if dataset else 0,
                "misleading_notes": misleading_notes,
                "with_api_data": len(dataset),  # All have API data now
                "all_original_tweets": True,
                "all_english_tweets": True,
                "note_status_breakdown": dict(status_counts),
                "total_duration": sum(d["video"]["duration_seconds"] for d in dataset),
            },
            "samples": dataset,
        }

        # Create timestamped directory for this dataset
        dataset_dir = datasets_dir / f"dataset_{timestamp}"
        dataset_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON in timestamped directory
        json_file = dataset_dir / "dataset.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        logger.info(f"✓ Saved: {json_file}")

        # Save CSV - one row per tweet with comma-separated note info
        try:
            import pandas as pd

            flattened = []
            for entry in dataset:
                # Create one row per tweet with comma-separated note fields
                note_ids = ",".join(
                    note["note_id"] for note in entry["community_notes"]
                )
                note_statuses = ",".join(
                    note.get("current_status", "") or "UNKNOWN"
                    for note in entry["community_notes"]
                )
                note_classifications = ",".join(
                    note["classification"] or "" for note in entry["community_notes"]
                )
                is_misleading_flags = ",".join(
                    str(note["is_misleading"]) for note in entry["community_notes"]
                )

                flat = {
                    "sample_id": entry["metadata"]["sample_id"],
                    "tweet_id": entry["tweet"]["tweet_id"],
                    "tweet_url": entry["tweet"]["url"],
                    "tweet_text": entry["tweet"]["text"],
                    "tweet_author": entry["tweet"]["author_username"],
                    "tweet_likes": entry["tweet"]["engagement"]["likes"],
                    "tweet_created_at": entry["tweet"]["created_at"],
                    "video_filename": entry["video"]["filename"],
                    "video_duration": entry["video"]["duration_seconds"],
                    "num_notes": len(entry["community_notes"]),
                    "note_ids": note_ids,
                    "note_current_status": note_statuses,
                    "note_classifications": note_classifications,
                    "is_misleading": is_misleading_flags,
                }
                flattened.append(flat)

            csv_file = dataset_dir / "dataset.csv"
            df = pd.DataFrame(flattened)
            df.to_csv(csv_file, index=False, encoding="utf-8")
            logger.info(
                f"✓ Saved: {csv_file} ({len(flattened)} rows = tweets, {total_notes} notes)"
            )
        except Exception as e:
            logger.warning(f"Could not save CSV: {e}")

        # Create 'latest' symlink directory
        latest_dir = self.output_dir / "latest"

        # Remove old symlink/directory if exists
        if latest_dir.exists() or latest_dir.is_symlink():
            if latest_dir.is_symlink():
                latest_dir.unlink()
            else:
                import shutil

                shutil.rmtree(latest_dir)

        # Create symlink to latest dataset directory
        try:
            import os

            os.symlink(
                f"datasets/dataset_{timestamp}", latest_dir, target_is_directory=True
            )
            logger.info(
                f"✓ Created symlink: {latest_dir} -> datasets/dataset_{timestamp}"
            )
        except (OSError, NotImplementedError) as e:
            # Symlinks might not work on Windows, so copy files instead
            logger.warning(f"Could not create symlink (using copy instead): {e}")
            latest_dir.mkdir(exist_ok=True)
            import shutil

            shutil.copy2(json_file, latest_dir / "dataset.json")
            if csv_file.exists():
                shutil.copy2(csv_file, latest_dir / "dataset.csv")
            logger.info(f"✓ Copied to: {latest_dir}")

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
                total_notes = sum(len(d["community_notes"]) for d in dataset)
                logger.info(
                    f"Created {len(dataset)} tweet records with {total_notes} total notes"
                )

                # Save
                logger.info("\n💾 Saving dataset...")
                self.save_dataset(dataset)

                # Summary
                logger.info("\n" + "=" * 70)
                logger.info("✅ SUCCESS!")
                logger.info("=" * 70)
                logger.info(f"Total tweets: {len(dataset)}")
                logger.info(f"Total notes: {total_notes}")
                logger.info(
                    f"Average notes per tweet: {total_notes / len(dataset):.2f}"
                )

                # Count notes by status
                from collections import Counter

                status_counts = Counter()
                for entry in dataset:
                    for note in entry["community_notes"]:
                        status_counts[note.get("current_status", "UNKNOWN")] += 1

                logger.info("\nNote status breakdown:")
                for status, count in status_counts.most_common():
                    logger.info(f"  {status}: {count}")

                misleading_notes = sum(
                    1
                    for d in dataset
                    for note in d["community_notes"]
                    if note["is_misleading"]
                )
                logger.info(f"\nMisleading notes: {misleading_notes}")
                logger.info(f"All tweets are original (no retweets/replies): ✓")
                logger.info(f"All tweets are in English: ✓")
                logger.info(f"\nOutput:")
                logger.info(f"  Latest: {self.output_dir}/latest/dataset.json")
                logger.info(f"          {self.output_dir}/latest/dataset.csv")
                logger.info(
                    f"  Timestamped: {self.output_dir}/datasets/dataset_{{timestamp}}/dataset.{{json,csv}}"
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
        default=None,
        help="Random seed for reproducible sampling (default: random based on timestamp)",
    )
    parser.add_argument(
        "--note-status",
        type=str,
        default=None,
        help="Filter notes by status (e.g., CURRENTLY_RATED_HELPFUL, CURRENTLY_RATED_NOT_HELPFUL, NEEDS_MORE_RATINGS)",
    )
    parser.add_argument(
        "--tweet-ids-file",
        type=str,
        default=None,
        help="Path to file containing tweet IDs to include (one per line)",
    )
    args = parser.parse_args()

    # Load tweet IDs from file if provided
    tweet_ids = None
    if args.tweet_ids_file:
        tweet_ids_path = Path(args.tweet_ids_file)
        if tweet_ids_path.exists():
            with open(tweet_ids_path, "r") as f:
                tweet_ids = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(tweet_ids)} tweet IDs from {args.tweet_ids_file}")
        else:
            logger.error(f"Tweet IDs file not found: {args.tweet_ids_file}")
            sys.exit(1)

    creator = DatasetCreator(
        force_api_fetch=args.force_api_fetch,
        sample_size=args.sample_size,
        random_seed=args.random_seed,
        note_status_filter=args.note_status,
        tweet_ids=tweet_ids,
    )
    success = creator.run(use_api=not args.no_api)

    if success:
        print("\n✅ Dataset created successfully from database!")
        print("📁 Latest: data/evaluation/latest/dataset.json")
        print("📁 Latest: data/evaluation/latest/dataset.csv")
        print("📂 History: data/evaluation/datasets/dataset_*.{json,csv}")
    else:
        print("\n❌ Failed to create dataset")
        sys.exit(1)


if __name__ == "__main__":
    main()

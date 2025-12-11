#!/usr/bin/env python3
"""
Create Evaluation Dataset
ONE script that creates the complete evaluation dataset.
Handles everything: loading data, fetching tweets (if API available), creating output.
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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatasetCreator:
    """Creates the complete evaluation dataset in one go."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.videos_dir = self.data_dir / "videos"
        self.filtered_dir = self.data_dir / "filtered"
        self.output_dir = self.data_dir / "evaluation"
        self.output_dir.mkdir(exist_ok=True)

        self.twitter = TwitterService()

    def load_videos(self) -> List[Dict]:
        """Load downloaded videos."""
        videos_file = self.videos_dir / "downloaded_videos.json"

        with open(videos_file, "r") as f:
            videos = json.load(f)

        downloaded = [v for v in videos if v.get("downloaded", False)]
        logger.info(f"Loaded {len(downloaded)} downloaded videos")
        return downloaded

    def load_notes(self):
        """Load community notes."""
        try:
            import pandas as pd

            notes_file = self.filtered_dir / "verified_video_notes.csv"
            df = pd.read_csv(notes_file)
            logger.info(f"Loaded {len(df)} community notes")
            return df
        except ImportError:
            logger.error("pandas not installed: pip install pandas")
            return None

    def load_video_metadata(self) -> Dict[str, Dict]:
        """Load video info files for additional metadata."""
        video_info = {}

        for info_file in self.videos_dir.glob("*.info.json"):
            try:
                with open(info_file, "r") as f:
                    data = json.load(f)
                    video_id = info_file.stem.replace(".info", "")
                    video_info[video_id] = data
            except Exception as e:
                logger.warning(f"Could not load {info_file.name}: {e}")

        logger.info(f"Loaded {len(video_info)} video metadata files")
        return video_info

    def get_tweet_data(
        self, tweet_ids: List[str], use_api: bool = True
    ) -> Dict[str, Dict]:
        """
        Get tweet data. Try API first, fall back to video metadata.

        Args:
            tweet_ids: List of tweet IDs
            use_api: Whether to try Twitter API

        Returns:
            Dictionary of tweet data
        """
        tweet_data = {}

        # Try Twitter API if requested and available
        if use_api and self.twitter.is_available():
            logger.info("\n🔑 Twitter API available - fetching complete tweet data...")
            tweet_data = self.twitter.fetch_tweets(tweet_ids)

            if tweet_data:
                logger.info(f"✓ Fetched {len(tweet_data)} tweets from API")
                return tweet_data
            else:
                logger.warning("⚠️  API fetch failed, using video metadata")

        # Fall back to video metadata
        logger.info("📹 Using video metadata for tweet information")
        return {}

    def create_dataset(
        self, videos: List[Dict], notes_df, video_metadata: Dict, tweet_data: Dict
    ) -> List[Dict]:
        """Create the complete dataset."""
        import pandas as pd

        dataset = []

        # Create notes lookup
        notes_by_tweet = {}
        for _, note in notes_df.iterrows():
            tweet_id = str(note["tweetId"])
            notes_by_tweet[tweet_id] = note

        for video in videos:
            tweet_id = str(video.get("tweet_id", ""))
            note = notes_by_tweet.get(tweet_id)

            if note is None:
                logger.warning(f"No note for {video.get('filename')}")
                continue

            # Get video metadata
            video_basename = Path(video.get("filename", "")).stem
            video_info = video_metadata.get(video_basename, {})

            # Get tweet data (from API or video metadata)
            api_tweet = tweet_data.get(tweet_id, {})

            # Build entry
            entry = {
                "video": {
                    "filename": video.get("filename", ""),
                    "index": video.get("index", 0),
                    "duration_seconds": video.get("duration", 0),
                    "path": f"data/videos/{video.get('filename', '')}",
                    "title": video.get("title", ""),
                    "uploader": video.get("uploader", ""),
                },
                "tweet": {
                    "tweet_id": tweet_id,
                    "url": video.get("url", ""),
                    # Use API data if available, fall back to video metadata
                    "text": api_tweet.get("text", video_info.get("description", "")),
                    "author_name": api_tweet.get(
                        "author_name", video.get("uploader", "")
                    ),
                    "author_username": api_tweet.get(
                        "author_username", video_info.get("uploader_id", "")
                    ),
                    "author_verified": api_tweet.get("author_verified", False),
                    "created_at": api_tweet.get(
                        "created_at", video_info.get("upload_date", "")
                    ),
                    "engagement": {
                        "likes": api_tweet.get(
                            "likes", video_info.get("like_count", 0)
                        ),
                        "retweets": api_tweet.get(
                            "retweets", video_info.get("repost_count", 0)
                        ),
                        "replies": api_tweet.get(
                            "replies", video_info.get("comment_count", 0)
                        ),
                        "views": video_info.get("view_count", 0),
                    },
                },
                "community_note": {
                    "note_id": str(note.get("noteId", "")),
                    "classification": note.get("classification", ""),
                    "summary": note.get("summary", ""),
                    "is_misleading": note.get("classification", "")
                    == "MISINFORMED_OR_POTENTIALLY_MISLEADING",
                    "created_at_millis": int(note.get("createdAtMillis", 0)),
                    "reasons": {
                        "factual_error": int(note.get("misleadingFactualError", 0)),
                        "manipulated_media": int(
                            note.get("misleadingManipulatedMedia", 0)
                        ),
                        "missing_context": int(
                            note.get("misleadingMissingImportantContext", 0)
                        ),
                        "outdated_info": int(
                            note.get("misleadingOutdatedInformation", 0)
                        ),
                        "unverified_claim": int(
                            note.get("misleadingUnverifiedClaimAsFact", 0)
                        ),
                    },
                },
                "metadata": {
                    "sample_id": f"video_{video.get('index', 0):03d}",
                    "has_api_data": bool(api_tweet),
                    "created_at": datetime.now().isoformat(),
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
        Create the complete dataset.

        Args:
            use_api: Whether to use Twitter API if available

        Returns:
            Success status
        """
        logger.info("=" * 70)
        logger.info("CREATING EVALUATION DATASET")
        logger.info("=" * 70)

        try:
            # Load all data
            logger.info("\n📂 Loading data...")
            videos = self.load_videos()
            notes_df = self.load_notes()
            video_metadata = self.load_video_metadata()

            if notes_df is None:
                return False

            # Get tweet data
            tweet_ids = [str(v.get("tweet_id", "")) for v in videos]
            tweet_data = self.get_tweet_data(tweet_ids, use_api=use_api)

            # Create dataset
            logger.info("\n🔨 Creating dataset...")
            dataset = self.create_dataset(videos, notes_df, video_metadata, tweet_data)
            logger.info(f"Created {len(dataset)} samples")

            # Save
            logger.info("\n💾 Saving dataset...")
            self.save_dataset(dataset)

            # Summary
            logger.info("\n" + "=" * 70)
            logger.info("✅ SUCCESS!")
            logger.info("=" * 70)
            logger.info(f"Total samples: {len(dataset)}")
            logger.info(
                f"With API data: {sum(1 for d in dataset if d['metadata']['has_api_data'])}"
            )
            logger.info(
                f"Misleading: {sum(1 for d in dataset if d['community_note']['is_misleading'])}"
            )
            logger.info(f"\nOutput: {self.output_dir}/dataset.json")
            logger.info(f"        {self.output_dir}/dataset.csv")

            if not tweet_data and use_api:
                logger.info("\n💡 To get complete tweet data:")
                logger.info("   1. Get Twitter API credentials")
                logger.info("   2. Add TWITTER_BEARER_TOKEN to .env")
                logger.info("   3. Run again")

            return True

        except Exception as e:
            logger.error(f"Failed to create dataset: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Create evaluation dataset")
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="Don't use Twitter API even if available",
    )
    args = parser.parse_args()

    creator = DatasetCreator()
    success = creator.run(use_api=not args.no_api)

    if success:
        print("\n✅ Dataset created successfully!")
        print("📁 Check data/evaluation/dataset.json")
    else:
        print("\n❌ Failed to create dataset")
        sys.exit(1)


if __name__ == "__main__":
    main()

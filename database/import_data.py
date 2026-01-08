"""
Data import utilities for populating the database from CSV/JSON files.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from tqdm import tqdm

from database.models import Note, Tweet, MediaMetadata

logger = logging.getLogger(__name__)


def import_notes_from_tsv(
    session: Session,
    tsv_path: Path,
    batch_size: int = 1000,
    create_tweet_stubs: bool = True,
) -> Dict[str, int]:
    """
    Import notes from raw TSV file.

    Args:
        session: Database session
        tsv_path: Path to notes-00000.tsv file
        batch_size: Number of records to commit at once
        create_tweet_stubs: If True, create tweet stub records first

    Returns:
        Dictionary with import statistics
    """
    logger.info(f"Importing notes from {tsv_path}")

    # First pass: collect all unique tweet IDs if we need to create stubs
    if create_tweet_stubs:
        logger.info("First pass: collecting unique tweet IDs...")
        tweet_ids = set()
        with open(tsv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in tqdm(reader, desc="Collecting tweet IDs"):
                if row.get("tweetId"):
                    try:
                        tweet_ids.add(int(row["tweetId"]))
                    except ValueError:
                        pass

        logger.info(f"Found {len(tweet_ids)} unique tweet IDs")
        logger.info("Creating tweet stub records...")
        created = ensure_tweets_exist(session, list(tweet_ids))
        logger.info(f"Created {created} new tweet records")

    stats = {"total": 0, "imported": 0, "skipped": 0, "errors": 0}

    with open(tsv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        batch = []

        for row in tqdm(reader, desc="Importing notes"):
            stats["total"] += 1

            try:
                # Convert empty strings to None
                def clean_value(value):
                    if value == "" or value is None:
                        return None
                    return value

                # Convert integer fields
                def to_int(value):
                    if value == "" or value is None:
                        return None
                    try:
                        return int(value)
                    except ValueError:
                        return None

                # Convert boolean fields
                def to_bool(value):
                    if value == "" or value is None:
                        return None
                    return value == "1" or value.lower() == "true"

                note = Note(
                    note_id=int(row["noteId"]),
                    note_author_participant_id=clean_value(
                        row["noteAuthorParticipantId"]
                    ),
                    created_at_millis=int(row["createdAtMillis"]),
                    tweet_id=int(row["tweetId"]) if row["tweetId"] else None,
                    classification=clean_value(row["classification"]),
                    believable=clean_value(row.get("believable")),
                    harmful=clean_value(row.get("harmful")),
                    validation_difficulty=clean_value(row.get("validationDifficulty")),
                    misleading_other=to_int(row.get("misleadingOther")),
                    misleading_factual_error=to_int(row.get("misleadingFactualError")),
                    misleading_manipulated_media=to_int(
                        row.get("misleadingManipulatedMedia")
                    ),
                    misleading_outdated_information=to_int(
                        row.get("misleadingOutdatedInformation")
                    ),
                    misleading_missing_important_context=to_int(
                        row.get("misleadingMissingImportantContext")
                    ),
                    misleading_unverified_claim_as_fact=to_int(
                        row.get("misleadingUnverifiedClaimAsFact")
                    ),
                    misleading_satire=to_int(row.get("misleadingSatire")),
                    not_misleading_other=to_int(row.get("notMisleadingOther")),
                    not_misleading_factually_correct=to_int(
                        row.get("notMisleadingFactuallyCorrect")
                    ),
                    not_misleading_outdated_but_not_when_written=to_int(
                        row.get("notMisleadingOutdatedButNotWhenWritten")
                    ),
                    not_misleading_clearly_satire=to_int(
                        row.get("notMisleadingClearlySatire")
                    ),
                    not_misleading_personal_opinion=to_int(
                        row.get("notMisleadingPersonalOpinion")
                    ),
                    trustworthy_sources=to_int(row.get("trustworthySources")),
                    summary=clean_value(row.get("summary")),
                    is_media_note=to_bool(row.get("isMediaNote")),
                    note_url=f"https://twitter.com/i/birdwatch/n/{int(row['noteId'])}",
                )

                batch.append(note)

                # Commit in batches
                if len(batch) >= batch_size:
                    try:
                        session.bulk_save_objects(batch)
                        session.commit()
                        stats["imported"] += len(batch)
                        batch = []
                    except IntegrityError as e:
                        session.rollback()
                        logger.warning(f"Batch import failed: {e}")
                        stats["errors"] += len(batch)
                        batch = []

            except Exception as e:
                logger.debug(f"Error processing note row: {e}")
                stats["errors"] += 1

        # Commit remaining batch
        if batch:
            try:
                session.bulk_save_objects(batch)
                session.commit()
                stats["imported"] += len(batch)
            except IntegrityError as e:
                session.rollback()
                logger.warning(f"Final batch import failed: {e}")
                stats["errors"] += len(batch)

    logger.info(f"Note import complete: {stats}")
    return stats


def import_tweets_from_api_data(
    session: Session,
    tweets_data: Dict[str, Dict],
) -> Dict[str, int]:
    """
    Import tweets from Twitter API data dictionary.

    Args:
        session: Database session
        tweets_data: Dictionary mapping tweet_id to tweet data

    Returns:
        Dictionary with import statistics
    """
    logger.info(f"Importing {len(tweets_data)} tweets from API data")

    stats = {"total": len(tweets_data), "imported": 0, "updated": 0, "errors": 0}

    for tweet_id_str, data in tqdm(tweets_data.items(), desc="Importing tweets"):
        try:
            tweet_id = int(tweet_id_str)

            # Check if tweet already exists
            existing_tweet = (
                session.query(Tweet).filter(Tweet.tweet_id == tweet_id).first()
            )

            # Parse created_at if it's a string
            created_at = None
            if data.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(
                        data["created_at"].replace("Z", "+00:00")
                    )
                except:
                    pass

            tweet_data = {
                "tweet_id": tweet_id,
                "text": data.get("text"),
                "created_at": created_at,
                "author_id": data.get("author_id"),
                "author_name": data.get("author_name"),
                "author_username": data.get("author_username"),
                "author_verified": data.get("author_verified"),
                "likes": data.get("likes"),
                "retweets": data.get("retweets"),
                "replies": data.get("replies"),
                "quotes": data.get("quotes"),
                "tweet_url": f"https://twitter.com/i/status/{tweet_id}",
                "raw_api_data": data,  # Store complete API response
                "api_fetched_at": datetime.utcnow(),
            }

            if existing_tweet:
                # Update existing tweet
                for key, value in tweet_data.items():
                    if key != "tweet_id":  # Don't update primary key
                        setattr(existing_tweet, key, value)
                stats["updated"] += 1
            else:
                # Create new tweet
                tweet = Tweet(**tweet_data)
                session.add(tweet)
                stats["imported"] += 1

            session.commit()

        except Exception as e:
            session.rollback()
            logger.error(f"Error importing tweet {tweet_id_str}: {e}")
            stats["errors"] += 1

    logger.info(f"Tweet import complete: {stats}")
    return stats


def import_media_metadata_from_json(
    session: Session, json_files_dir: Path, batch_size: int = 100
) -> Dict[str, int]:
    """
    Import media metadata from yt-dlp info.json files.

    Args:
        session: Database session
        json_files_dir: Directory containing *.info.json files
        batch_size: Number of records to commit at once

    Returns:
        Dictionary with import statistics
    """
    logger.info(f"Importing media metadata from {json_files_dir}")

    stats = {"total": 0, "imported": 0, "updated": 0, "errors": 0}

    # Find all info.json files
    info_files = list(json_files_dir.glob("*.info.json"))
    batch = []

    for info_file in tqdm(info_files, desc="Importing media metadata"):
        stats["total"] += 1

        try:
            with open(info_file, "r", encoding="utf-8") as f:
                info = json.load(f)

            # Extract tweet_id from filename or info
            tweet_id = None
            if "id" in info:
                tweet_id = int(info["id"])
            else:
                # Try to extract from filename (e.g., video_001_1234567890.info.json)
                parts = info_file.stem.split("_")
                for part in parts:
                    if part.isdigit() and len(part) > 10:
                        tweet_id = int(part)
                        break

            if not tweet_id:
                logger.warning(f"Could not extract tweet_id from {info_file}")
                stats["errors"] += 1
                continue

            # Check if media metadata already exists
            existing = (
                session.query(MediaMetadata)
                .filter(MediaMetadata.tweet_id == tweet_id)
                .first()
            )

            # Extract resolution from formats if available
            width = info.get("width")
            height = info.get("height")

            media_data = {
                "tweet_id": tweet_id,
                "media_id": str(info.get("id", "")),
                "media_type": info.get("_type", "video"),  # Default to video
                "title": info.get("title"),
                "description": info.get("description"),
                "uploader": info.get("uploader"),
                "uploader_id": info.get("uploader_id"),
                "timestamp": info.get("timestamp"),
                "duration_ms": (
                    int(info.get("duration", 0) * 1000)
                    if info.get("duration")
                    else None
                ),
                "like_count": info.get("like_count"),
                "width": width,
                "height": height,
                "formats": info.get("formats"),  # Store as JSONB
                "local_path": str(
                    info_file.parent / info_file.stem.replace(".info", "")
                ),
            }

            if existing:
                # Update existing
                for key, value in media_data.items():
                    if key != "tweet_id":
                        setattr(existing, key, value)
                stats["updated"] += 1
            else:
                # Create new
                media = MediaMetadata(**media_data)
                batch.append(media)

            # Commit in batches
            if len(batch) >= batch_size:
                try:
                    session.bulk_save_objects(batch)
                    session.commit()
                    stats["imported"] += len(batch)
                    batch = []
                except IntegrityError as e:
                    session.rollback()
                    logger.warning(f"Batch import failed: {e}")
                    stats["errors"] += len(batch)
                    batch = []

        except Exception as e:
            logger.error(f"Error processing {info_file}: {e}")
            stats["errors"] += 1

    # Commit remaining batch
    if batch:
        try:
            session.bulk_save_objects(batch)
            session.commit()
            stats["imported"] += len(batch)
        except IntegrityError as e:
            session.rollback()
            logger.warning(f"Final batch import failed: {e}")
            stats["errors"] += len(batch)

    logger.info(f"Media metadata import complete: {stats}")
    return stats


def ensure_tweets_exist(
    session: Session, tweet_ids: List[int], batch_size: int = 5000
) -> int:
    """
    Ensure tweet records exist for the given IDs (create stub records if needed).

    Args:
        session: Database session
        tweet_ids: List of tweet IDs
        batch_size: Number of records to check/create at once

    Returns:
        Number of tweet stubs created
    """
    created = 0

    # Process in batches for efficiency
    for i in tqdm(range(0, len(tweet_ids), batch_size), desc="Ensuring tweets exist"):
        batch_ids = tweet_ids[i : i + batch_size]

        # Get existing tweet IDs in this batch
        existing_ids = set(
            row[0]
            for row in session.query(Tweet.tweet_id)
            .filter(Tweet.tweet_id.in_(batch_ids))
            .all()
        )

        # Create missing tweets
        missing_ids = set(batch_ids) - existing_ids
        if missing_ids:
            tweets = [Tweet(tweet_id=tid) for tid in missing_ids]
            session.bulk_save_objects(tweets)
            session.commit()
            created += len(missing_ids)

    return created

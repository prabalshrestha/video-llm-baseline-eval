#!/usr/bin/env python
"""
Import data from CSV exports into PostgreSQL database.

This script imports data from the data/exports directory:
- tweets_*.csv
- notes_*.csv  
- media_metadata_*.csv

The script handles:
- Data type conversions (dates, JSON, booleans)
- Bulk inserts for efficiency
- Progress tracking
- Duplicate handling
"""

import argparse
import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from tqdm import tqdm

from database.config import SessionLocal, check_connection
from database.models import Tweet, Note, MediaMetadata

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_latest_export_files(exports_dir: Path) -> Dict[str, Optional[Path]]:
    """
    Find the latest export files in the exports directory.
    
    Args:
        exports_dir: Path to the exports directory
        
    Returns:
        Dictionary with 'tweets', 'notes', 'media_metadata' keys and file paths
    """
    files = {
        'tweets': None,
        'notes': None,
        'media_metadata': None
    }
    
    for file_type in files.keys():
        pattern = f"{file_type}_*.csv"
        matching_files = list(exports_dir.glob(pattern))
        if matching_files:
            # Get the most recent file
            files[file_type] = sorted(matching_files)[-1]
            logger.info(f"Found {file_type} file: {files[file_type].name}")
        else:
            logger.warning(f"No {file_type} file found matching pattern: {pattern}")
    
    return files


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse datetime from various formats."""
    if pd.isna(value) or value == '':
        return None
    
    if isinstance(value, datetime):
        return value
    
    try:
        # Try ISO format first
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        pass
    
    try:
        # Try common formats
        return pd.to_datetime(value)
    except:
        logger.warning(f"Could not parse datetime: {value}")
        return None


def parse_json(value: Any) -> Optional[Dict]:
    """Parse JSON string to dictionary."""
    if pd.isna(value) or value == '':
        return None
    
    if isinstance(value, dict):
        return value
    
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Could not parse JSON: {value[:100]}...")
        return None


def parse_boolean(value: Any) -> Optional[bool]:
    """Parse boolean from various formats."""
    if pd.isna(value) or value == '':
        return None
    
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 't')
    
    return bool(value)


def import_tweets(session, csv_path: Path, batch_size: int = 1000) -> Dict[str, int]:
    """
    Import tweets from CSV file.
    
    Args:
        session: SQLAlchemy session
        csv_path: Path to tweets CSV file
        batch_size: Number of records to insert at once
        
    Returns:
        Statistics dictionary
    """
    logger.info(f"Reading tweets from {csv_path}...")
    df = pd.read_csv(csv_path, dtype={'tweet_id': str, 'author_id': str})
    
    logger.info(f"Processing {len(df)} tweets...")
    stats = {'total': len(df), 'inserted': 0, 'updated': 0, 'errors': 0}
    
    # Process in batches
    for i in tqdm(range(0, len(df), batch_size), desc="Importing tweets"):
        batch = df.iloc[i:i+batch_size]
        records = []
        
        for _, row in batch.iterrows():
            try:
                record = {
                    'tweet_id': int(row['tweet_id']) if pd.notna(row['tweet_id']) else None,
                    'text': row['text'] if pd.notna(row['text']) else None,
                    'created_at': parse_datetime(row['created_at']),
                    'author_id': row['author_id'] if pd.notna(row['author_id']) else None,
                    'author_name': row['author_name'] if pd.notna(row['author_name']) else None,
                    'author_username': row['author_username'] if pd.notna(row['author_username']) else None,
                    'author_verified': parse_boolean(row['author_verified']),
                    'likes': int(row['likes']) if pd.notna(row['likes']) else None,
                    'retweets': int(row['retweets']) if pd.notna(row['retweets']) else None,
                    'replies': int(row['replies']) if pd.notna(row['replies']) else None,
                    'quotes': int(row['quotes']) if pd.notna(row['quotes']) else None,
                    'is_verified_video': parse_boolean(row['is_verified_video']),
                    'media_type': row['media_type'] if pd.notna(row['media_type']) else None,
                    'raw_api_data': parse_json(row['raw_api_data']),
                    'api_fetched_at': parse_datetime(row['api_fetched_at']),
                }
                
                if record['tweet_id']:
                    records.append(record)
            except Exception as e:
                logger.error(f"Error processing tweet row: {e}")
                stats['errors'] += 1
        
        # Bulk upsert
        if records:
            try:
                stmt = insert(Tweet).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['tweet_id'],
                    set_={
                        'text': stmt.excluded.text,
                        'created_at': stmt.excluded.created_at,
                        'author_id': stmt.excluded.author_id,
                        'author_name': stmt.excluded.author_name,
                        'author_username': stmt.excluded.author_username,
                        'author_verified': stmt.excluded.author_verified,
                        'likes': stmt.excluded.likes,
                        'retweets': stmt.excluded.retweets,
                        'replies': stmt.excluded.replies,
                        'quotes': stmt.excluded.quotes,
                        'is_verified_video': stmt.excluded.is_verified_video,
                        'media_type': stmt.excluded.media_type,
                        'raw_api_data': stmt.excluded.raw_api_data,
                        'api_fetched_at': stmt.excluded.api_fetched_at,
                    }
                )
                session.execute(stmt)
                session.commit()
                stats['inserted'] += len(records)
            except Exception as e:
                logger.error(f"Error inserting tweet batch: {e}")
                session.rollback()
                stats['errors'] += len(records)
    
    return stats


def import_notes(session, csv_path: Path, batch_size: int = 1000) -> Dict[str, int]:
    """
    Import notes from CSV file.
    
    Args:
        session: SQLAlchemy session
        csv_path: Path to notes CSV file
        batch_size: Number of records to insert at once
        
    Returns:
        Statistics dictionary
    """
    logger.info(f"Reading notes from {csv_path}...")
    df = pd.read_csv(csv_path, dtype={'note_id': str, 'tweet_id': str})
    
    logger.info(f"Processing {len(df)} notes...")
    stats = {'total': len(df), 'inserted': 0, 'updated': 0, 'errors': 0}
    
    # Process in batches
    for i in tqdm(range(0, len(df), batch_size), desc="Importing notes"):
        batch = df.iloc[i:i+batch_size]
        records = []
        
        for _, row in batch.iterrows():
            try:
                record = {
                    'note_id': int(row['note_id']) if pd.notna(row['note_id']) else None,
                    'tweet_id': int(row['tweet_id']) if pd.notna(row['tweet_id']) else None,
                    'note_author_participant_id': row['note_author_participant_id'] if pd.notna(row['note_author_participant_id']) else '',
                    'created_at_millis': int(row['created_at_millis']) if pd.notna(row['created_at_millis']) else None,
                    'classification': row['classification'] if pd.notna(row['classification']) else None,
                    'believable': row['believable'] if pd.notna(row['believable']) else None,
                    'harmful': row['harmful'] if pd.notna(row['harmful']) else None,
                    'validation_difficulty': row['validation_difficulty'] if pd.notna(row['validation_difficulty']) else None,
                    'misleading_other': int(row['misleading_other']) if pd.notna(row['misleading_other']) else None,
                    'misleading_factual_error': int(row['misleading_factual_error']) if pd.notna(row['misleading_factual_error']) else None,
                    'misleading_manipulated_media': int(row['misleading_manipulated_media']) if pd.notna(row['misleading_manipulated_media']) else None,
                    'misleading_outdated_information': int(row['misleading_outdated_information']) if pd.notna(row['misleading_outdated_information']) else None,
                    'misleading_missing_important_context': int(row['misleading_missing_important_context']) if pd.notna(row['misleading_missing_important_context']) else None,
                    'misleading_unverified_claim_as_fact': int(row['misleading_unverified_claim_as_fact']) if pd.notna(row['misleading_unverified_claim_as_fact']) else None,
                    'misleading_satire': int(row['misleading_satire']) if pd.notna(row['misleading_satire']) else None,
                    'not_misleading_other': int(row['not_misleading_other']) if pd.notna(row['not_misleading_other']) else None,
                    'not_misleading_factually_correct': int(row['not_misleading_factually_correct']) if pd.notna(row['not_misleading_factually_correct']) else None,
                    'not_misleading_outdated_but_not_when_written': int(row['not_misleading_outdated_but_not_when_written']) if pd.notna(row['not_misleading_outdated_but_not_when_written']) else None,
                    'not_misleading_clearly_satire': int(row['not_misleading_clearly_satire']) if pd.notna(row['not_misleading_clearly_satire']) else None,
                    'not_misleading_personal_opinion': int(row['not_misleading_personal_opinion']) if pd.notna(row['not_misleading_personal_opinion']) else None,
                    'trustworthy_sources': int(row['trustworthy_sources']) if pd.notna(row['trustworthy_sources']) else None,
                    'summary': row['summary'] if pd.notna(row['summary']) else None,
                    'is_media_note': parse_boolean(row['is_media_note']),
                }
                
                if record['note_id'] and record['tweet_id']:
                    records.append(record)
            except Exception as e:
                logger.error(f"Error processing note row: {e}")
                stats['errors'] += 1
        
        # Bulk upsert
        if records:
            try:
                stmt = insert(Note).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['note_id'],
                    set_={k: v for k, v in stmt.excluded.items() if k != 'note_id'}
                )
                session.execute(stmt)
                session.commit()
                stats['inserted'] += len(records)
            except Exception as e:
                logger.error(f"Error inserting note batch: {e}")
                session.rollback()
                stats['errors'] += len(records)
    
    return stats


def import_media_metadata(session, csv_path: Path, batch_size: int = 500) -> Dict[str, int]:
    """
    Import media metadata from CSV file.
    
    Args:
        session: SQLAlchemy session
        csv_path: Path to media metadata CSV file
        batch_size: Number of records to insert at once
        
    Returns:
        Statistics dictionary
    """
    logger.info(f"Reading media metadata from {csv_path}...")
    df = pd.read_csv(csv_path, dtype={'tweet_id': str, 'media_id': str})
    
    logger.info(f"Processing {len(df)} media metadata records...")
    stats = {'total': len(df), 'inserted': 0, 'updated': 0, 'errors': 0}
    
    # Process in batches
    for i in tqdm(range(0, len(df), batch_size), desc="Importing media metadata"):
        batch = df.iloc[i:i+batch_size]
        records = []
        
        for _, row in batch.iterrows():
            try:
                record = {
                    'tweet_id': int(row['tweet_id']) if pd.notna(row['tweet_id']) else None,
                    'media_id': row['media_id'] if pd.notna(row['media_id']) else None,
                    'media_type': row['media_type'] if pd.notna(row['media_type']) else None,
                    'title': row['title'] if pd.notna(row['title']) else None,
                    'description': row['description'] if pd.notna(row['description']) else None,
                    'uploader': row['uploader'] if pd.notna(row['uploader']) else None,
                    'uploader_id': row['uploader_id'] if pd.notna(row['uploader_id']) else None,
                    'timestamp': int(row['timestamp']) if pd.notna(row['timestamp']) else None,
                    'duration_ms': int(row['duration_ms']) if pd.notna(row['duration_ms']) else None,
                    'like_count': int(row['like_count']) if pd.notna(row['like_count']) else None,
                    'width': int(row['width']) if pd.notna(row['width']) else None,
                    'height': int(row['height']) if pd.notna(row['height']) else None,
                    'formats': parse_json(row['formats']),
                    'local_path': row['local_path'] if pd.notna(row['local_path']) else None,
                }
                
                if record['tweet_id']:
                    records.append(record)
            except Exception as e:
                logger.error(f"Error processing media metadata row: {e}")
                stats['errors'] += 1
        
        # Bulk upsert
        if records:
            try:
                stmt = insert(MediaMetadata).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['tweet_id'],
                    set_={k: v for k, v in stmt.excluded.items() if k != 'tweet_id'}
                )
                session.execute(stmt)
                session.commit()
                stats['inserted'] += len(records)
            except Exception as e:
                logger.error(f"Error inserting media metadata batch: {e}")
                session.rollback()
                stats['errors'] += len(records)
    
    return stats


def verify_import(session) -> Dict[str, int]:
    """Verify imported data and return counts."""
    counts = {}
    
    try:
        counts['tweets'] = session.execute(text("SELECT COUNT(*) FROM tweets")).scalar()
        counts['notes'] = session.execute(text("SELECT COUNT(*) FROM notes")).scalar()
        counts['media_metadata'] = session.execute(text("SELECT COUNT(*) FROM media_metadata")).scalar()
    except Exception as e:
        logger.error(f"Error verifying import: {e}")
        return {}
    
    return counts


def main():
    """Main import function."""
    parser = argparse.ArgumentParser(
        description="Import data from CSV exports to PostgreSQL database"
    )
    parser.add_argument(
        "--exports-dir",
        type=Path,
        default=Path("data/exports"),
        help="Directory containing export CSV files"
    )
    parser.add_argument(
        "--tweets-file",
        type=Path,
        help="Specific tweets CSV file (overrides auto-detection)"
    )
    parser.add_argument(
        "--notes-file",
        type=Path,
        help="Specific notes CSV file (overrides auto-detection)"
    )
    parser.add_argument(
        "--media-file",
        type=Path,
        help="Specific media metadata CSV file (overrides auto-detection)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of records to insert per batch"
    )
    parser.add_argument(
        "--skip-tweets",
        action="store_true",
        help="Skip importing tweets"
    )
    parser.add_argument(
        "--skip-notes",
        action="store_true",
        help="Skip importing notes"
    )
    parser.add_argument(
        "--skip-media",
        action="store_true",
        help="Skip importing media metadata"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Data Import from CSV Exports")
    logger.info("=" * 60)
    
    # Check database connection
    logger.info("Checking database connection...")
    if not check_connection():
        logger.error("Cannot connect to database. Exiting.")
        sys.exit(1)
    
    # Find export files
    if args.tweets_file or args.notes_file or args.media_file:
        files = {
            'tweets': args.tweets_file,
            'notes': args.notes_file,
            'media_metadata': args.media_file
        }
    else:
        if not args.exports_dir.exists():
            logger.error(f"Exports directory not found: {args.exports_dir}")
            sys.exit(1)
        
        files = find_latest_export_files(args.exports_dir)
    
    # Create session
    session = SessionLocal()
    
    try:
        # Import in order: tweets -> notes -> media_metadata
        
        # 1. Import tweets
        if not args.skip_tweets and files['tweets']:
            logger.info("=" * 60)
            logger.info("Importing tweets...")
            stats = import_tweets(session, files['tweets'], args.batch_size)
            logger.info(f"Tweets import complete: {stats}")
        else:
            logger.info("Skipping tweets import")
        
        # 2. Import notes
        if not args.skip_notes and files['notes']:
            logger.info("=" * 60)
            logger.info("Importing notes...")
            stats = import_notes(session, files['notes'], args.batch_size)
            logger.info(f"Notes import complete: {stats}")
        else:
            logger.info("Skipping notes import")
        
        # 3. Import media metadata
        if not args.skip_media and files['media_metadata']:
            logger.info("=" * 60)
            logger.info("Importing media metadata...")
            stats = import_media_metadata(session, files['media_metadata'], args.batch_size)
            logger.info(f"Media metadata import complete: {stats}")
        else:
            logger.info("Skipping media metadata import")
        
        # Verify import
        logger.info("=" * 60)
        logger.info("Verifying import...")
        counts = verify_import(session)
        logger.info("Final database counts:")
        for table, count in counts.items():
            logger.info(f"  {table}: {count:,}")
        
        logger.info("=" * 60)
        logger.info("✓ Import completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()


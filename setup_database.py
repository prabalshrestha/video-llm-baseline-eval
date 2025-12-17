#!/usr/bin/env python
"""
Database setup script for Video LLM Evaluation project.

This script:
1. Checks PostgreSQL connection
2. Runs database migrations
3. Optionally imports existing data
4. Verifies data integrity
"""

import argparse
import logging
import sys
from pathlib import Path
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_database_connection():
    """Check if PostgreSQL database is accessible."""
    logger.info("Checking database connection...")
    
    from database.config import check_connection, get_database_url
    
    logger.info(f"Database URL: {get_database_url()}")
    
    if check_connection():
        logger.info("✓ Database connection successful")
        return True
    else:
        logger.error("✗ Database connection failed")
        logger.error("Please ensure PostgreSQL is running and DATABASE_URL is set correctly")
        logger.error("Example: export DATABASE_URL='postgresql://user:pass@localhost/video_llm_eval'")
        return False


def run_migrations():
    """Run Alembic migrations to create/update schema."""
    logger.info("Running database migrations...")
    
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(result.stdout)
        logger.info("✓ Migrations completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Migration failed: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("✗ Alembic not found. Install with: pip install alembic")
        return False


def import_data(import_notes=False, import_tweets=False, import_media=False):
    """Import data from existing files."""
    from database.config import SessionLocal
    from database.import_data import (
        import_notes_from_tsv,
        import_tweets_from_api_data,
        import_media_metadata_from_json,
        ensure_tweets_exist
    )
    
    session = SessionLocal()
    
    try:
        # Import notes first
        if import_notes:
            logger.info("=" * 60)
            logger.info("Importing notes from TSV...")
            notes_path = Path("data/raw/notes-00000.tsv")
            
            if notes_path.exists():
                stats = import_notes_from_tsv(session, notes_path)
                logger.info(f"Notes import stats: {stats}")
                
                # Ensure tweet stubs exist for all notes
                logger.info("Creating tweet stubs for notes...")
                from database.models import Note
                tweet_ids = session.query(Note.tweet_id).distinct().all()
                tweet_ids = [tid[0] for tid in tweet_ids if tid[0] is not None]
                created = ensure_tweets_exist(session, tweet_ids)
                logger.info(f"Created {created} tweet stub records")
            else:
                logger.warning(f"Notes file not found: {notes_path}")
        
        # Import Twitter API data
        if import_tweets:
            logger.info("=" * 60)
            logger.info("Importing tweets from API data...")
            # This would typically load from a saved API response file
            # For now, just log that it's available
            logger.info("To import Twitter API data, use the twitter_service module")
            logger.info("and pass the tweets_data dictionary to import_tweets_from_api_data()")
        
        # Import media metadata
        if import_media:
            logger.info("=" * 60)
            logger.info("Importing media metadata from info.json files...")
            videos_dir = Path("data/videos")
            
            if videos_dir.exists():
                stats = import_media_metadata_from_json(session, videos_dir)
                logger.info(f"Media metadata import stats: {stats}")
            else:
                logger.warning(f"Videos directory not found: {videos_dir}")
        
    except Exception as e:
        logger.error(f"Error during data import: {e}")
        session.rollback()
        return False
    finally:
        session.close()
    
    return True


def verify_data():
    """Verify data integrity and print statistics."""
    logger.info("=" * 60)
    logger.info("Verifying data integrity...")
    
    from database.config import SessionLocal
    from database.queries import get_engagement_stats
    
    session = SessionLocal()
    
    try:
        stats = get_engagement_stats(session)
        
        logger.info("Database Statistics:")
        logger.info(f"  Total tweets: {stats['total_tweets']}")
        logger.info(f"  Total notes: {stats['total_notes']}")
        logger.info(f"  Total media: {stats['total_media']}")
        logger.info(f"  Average likes: {stats['avg_likes']:.2f}")
        logger.info(f"  Maximum likes: {stats['max_likes']}")
        logger.info(f"  Misleading notes: {stats['misleading_count']}")
        logger.info(f"  Not misleading notes: {stats['not_misleading_count']}")
        
        logger.info("✓ Data verification complete")
        return True
        
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        return False
    finally:
        session.close()


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(
        description="Setup database for Video LLM Evaluation project"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check database connection"
    )
    parser.add_argument(
        "--migrate-only",
        action="store_true",
        help="Only run migrations"
    )
    parser.add_argument(
        "--import-notes",
        action="store_true",
        help="Import notes from raw TSV file"
    )
    parser.add_argument(
        "--import-tweets",
        action="store_true",
        help="Import tweets from API data"
    )
    parser.add_argument(
        "--import-media",
        action="store_true",
        help="Import media metadata from info.json files"
    )
    parser.add_argument(
        "--import-all",
        action="store_true",
        help="Import all available data"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify data integrity and show statistics"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Video LLM Evaluation Database Setup")
    logger.info("=" * 60)
    
    # Check database connection
    if not check_database_connection():
        logger.error("Setup failed: Cannot connect to database")
        sys.exit(1)
    
    if args.check_only:
        logger.info("Check complete. Exiting.")
        sys.exit(0)
    
    # Run migrations
    if not args.migrate_only or not args.check_only:
        if not run_migrations():
            logger.error("Setup failed: Migration error")
            sys.exit(1)
    
    if args.migrate_only:
        logger.info("Migration complete. Exiting.")
        sys.exit(0)
    
    # Import data if requested
    if args.import_all:
        args.import_notes = True
        args.import_tweets = True
        args.import_media = True
    
    if any([args.import_notes, args.import_tweets, args.import_media]):
        if not import_data(
            import_notes=args.import_notes,
            import_tweets=args.import_tweets,
            import_media=args.import_media
        ):
            logger.error("Setup failed: Data import error")
            sys.exit(1)
    
    # Verify data
    if args.verify or any([args.import_notes, args.import_tweets, args.import_media]):
        verify_data()
    
    logger.info("=" * 60)
    logger.info("✓ Database setup complete!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Import data: python setup_database.py --import-all")
    logger.info("  2. Verify data: python setup_database.py --verify")
    logger.info("  3. Query data: Use database.queries module")


if __name__ == "__main__":
    main()


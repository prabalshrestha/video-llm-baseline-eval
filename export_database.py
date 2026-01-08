#!/usr/bin/env python
"""
Export database tables to CSV files.

This script exports data from PostgreSQL to CSV files in data/exports/.
Useful for:
- Creating backups
- Transferring data between servers
- Sharing data with collaborators
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
from sqlalchemy import text
from tqdm import tqdm

from database.config import SessionLocal, check_connection
from database.models import Tweet, Note, MediaMetadata

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def export_table_to_csv(session, model, output_path: Path, chunk_size: int = 10000):
    """
    Export a SQLAlchemy model to CSV file in chunks.
    
    Args:
        session: SQLAlchemy session
        model: SQLAlchemy model class
        output_path: Path to output CSV file
        chunk_size: Number of rows to process at once
    """
    table_name = model.__tablename__
    logger.info(f"Exporting {table_name} to {output_path.name}...")
    
    # Get total count
    total = session.query(model).count()
    logger.info(f"Total rows: {total:,}")
    
    if total == 0:
        logger.warning(f"No data to export for {table_name}")
        return 0
    
    # Export in chunks
    first_chunk = True
    exported = 0
    
    with tqdm(total=total, desc=f"Exporting {table_name}") as pbar:
        for offset in range(0, total, chunk_size):
            # Query chunk
            chunk = session.query(model).offset(offset).limit(chunk_size).all()
            
            # Convert to dictionaries
            rows = []
            for obj in chunk:
                row = {}
                for column in model.__table__.columns:
                    value = getattr(obj, column.name)
                    
                    # Convert datetime to ISO format string
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    
                    # Convert dict/list to JSON string
                    elif isinstance(value, (dict, list)):
                        import json
                        value = json.dumps(value)
                    
                    row[column.name] = value
                
                rows.append(row)
            
            # Write to CSV
            df = pd.DataFrame(rows)
            
            if first_chunk:
                df.to_csv(output_path, index=False, mode='w')
                first_chunk = False
            else:
                df.to_csv(output_path, index=False, mode='a', header=False)
            
            exported += len(chunk)
            pbar.update(len(chunk))
    
    logger.info(f"✓ Exported {exported:,} rows to {output_path.name}")
    return exported


def main():
    """Main export function."""
    parser = argparse.ArgumentParser(
        description="Export database tables to CSV files"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/exports"),
        help="Directory to save export CSV files"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=10000,
        help="Number of rows to process at once"
    )
    parser.add_argument(
        "--skip-tweets",
        action="store_true",
        help="Skip exporting tweets"
    )
    parser.add_argument(
        "--skip-notes",
        action="store_true",
        help="Skip exporting notes"
    )
    parser.add_argument(
        "--skip-media",
        action="store_true",
        help="Skip exporting media metadata"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Database Export to CSV")
    logger.info("=" * 60)
    
    # Check database connection
    logger.info("Checking database connection...")
    if not check_connection():
        logger.error("Cannot connect to database. Exiting.")
        sys.exit(1)
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {args.output_dir}")
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    
    # Create session
    session = SessionLocal()
    
    try:
        stats = {}
        
        # Export tweets
        if not args.skip_tweets:
            logger.info("=" * 60)
            output_path = args.output_dir / f"tweets_{timestamp}.csv"
            stats['tweets'] = export_table_to_csv(
                session, Tweet, output_path, args.chunk_size
            )
        
        # Export notes
        if not args.skip_notes:
            logger.info("=" * 60)
            output_path = args.output_dir / f"notes_{timestamp}.csv"
            stats['notes'] = export_table_to_csv(
                session, Note, output_path, args.chunk_size
            )
        
        # Export media metadata
        if not args.skip_media:
            logger.info("=" * 60)
            output_path = args.output_dir / f"media_metadata_{timestamp}.csv"
            stats['media_metadata'] = export_table_to_csv(
                session, MediaMetadata, output_path, args.chunk_size
            )
        
        # Summary
        logger.info("=" * 60)
        logger.info("Export Summary:")
        for table, count in stats.items():
            logger.info(f"  {table}: {count:,} rows")
        
        logger.info("=" * 60)
        logger.info("✓ Export completed successfully!")
        logger.info(f"Files saved to: {args.output_dir}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()


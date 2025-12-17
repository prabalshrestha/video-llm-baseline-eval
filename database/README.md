# Database Module

PostgreSQL database for storing Community Notes data, tweet information, and media metadata.

## Overview

The database consists of 3 tables:

1. **`tweets`** - Central table storing tweet data and Twitter API information
2. **`notes`** - Community Notes with all 23 columns from raw TSV files
3. **`media_metadata`** - yt-dlp scraped metadata for videos and images

## Setup

### Prerequisites

- PostgreSQL 12+ installed and running
- Python 3.8+
- Required packages: `sqlalchemy`, `alembic`, `psycopg2-binary`

### Installation

1. Install dependencies:
```bash
pip install sqlalchemy alembic psycopg2-binary
```

2. Set database URL:
```bash
export DATABASE_URL='postgresql://user:password@localhost/video_llm_eval'
```

Or create a `.env` file:
```
DATABASE_URL=postgresql://user:password@localhost/video_llm_eval
```

3. Run setup script:
```bash
# Check connection only
python setup_database.py --check-only

# Run migrations
python setup_database.py --migrate-only

# Import all data
python setup_database.py --import-all

# Verify data
python setup_database.py --verify
```

## Usage

### Basic Queries

```python
from database import get_session, Note, Tweet, MediaMetadata
from database.queries import get_evaluation_dataset, get_misleading_media

# Get a session
with get_session() as session:
    # Query notes
    notes = session.query(Note).filter(
        Note.classification == 'MISINFORMED_OR_POTENTIALLY_MISLEADING'
    ).limit(10).all()
    
    # Get misleading videos
    misleading = get_misleading_media(
        session, 
        min_engagement=10000,
        media_type='video'
    )
    
    # Get evaluation dataset
    dataset = get_evaluation_dataset(session, limit=100)
```

### Importing Data

```python
from pathlib import Path
from database.config import SessionLocal
from database.import_data import (
    import_notes_from_tsv,
    import_tweets_from_api_data,
    import_media_metadata_from_json
)

session = SessionLocal()

# Import notes
stats = import_notes_from_tsv(session, Path("data/raw/notes-00000.tsv"))
print(f"Imported {stats['imported']} notes")

# Import Twitter API data
tweets_data = {
    "1234567890": {
        "tweet_id": "1234567890",
        "text": "Example tweet",
        "author_name": "User",
        # ... more fields
    }
}
stats = import_tweets_from_api_data(session, tweets_data)

# Import media metadata
stats = import_media_metadata_from_json(session, Path("data/videos"))

session.close()
```

### Advanced Queries

```python
from sqlalchemy import func
from database.models import Note, Tweet, MediaMetadata

with get_session() as session:
    # Join all tables
    results = (
        session.query(Note, Tweet, MediaMetadata)
        .join(Tweet, Note.tweet_id == Tweet.tweet_id)
        .outerjoin(MediaMetadata, Tweet.tweet_id == MediaMetadata.tweet_id)
        .filter(
            Note.is_media_note == True,
            Tweet.likes > 5000
        )
        .all()
    )
    
    # Aggregate statistics
    stats = (
        session.query(
            Note.classification,
            func.count(Note.note_id).label('count'),
            func.avg(Tweet.likes).label('avg_likes')
        )
        .join(Tweet, Note.tweet_id == Tweet.tweet_id)
        .group_by(Note.classification)
        .all()
    )
    
    # Access JSONB fields
    tweets_with_api_data = (
        session.query(Tweet)
        .filter(Tweet.raw_api_data.isnot(None))
        .all()
    )
    
    for tweet in tweets_with_api_data:
        # Access nested JSONB data
        api_data = tweet.raw_api_data
        print(f"Tweet {tweet.tweet_id}: {api_data}")
```

## Schema

### tweets table

| Column | Type | Description |
|--------|------|-------------|
| tweet_id | BigInteger | Primary key |
| text | Text | Tweet content |
| created_at | DateTime | Tweet creation time |
| author_id | String | Author ID |
| author_name | String | Author display name |
| author_username | String | Author username |
| author_verified | Boolean | Verification status |
| likes | Integer | Number of likes |
| retweets | Integer | Number of retweets |
| replies | Integer | Number of replies |
| quotes | Integer | Number of quotes |
| is_verified_video | Boolean | Has verified video |
| media_type | String | Type of media (video/image) |
| raw_api_data | JSONB | Complete API response |
| api_fetched_at | DateTime | API fetch timestamp |

### notes table

| Column | Type | Description |
|--------|------|-------------|
| note_id | BigInteger | Primary key |
| tweet_id | BigInteger | Foreign key to tweets |
| note_author_participant_id | String | Note author ID |
| created_at_millis | BigInteger | Creation timestamp |
| classification | String | Note classification |
| believable | String | Believability rating |
| harmful | String | Harm rating |
| validation_difficulty | String | Validation difficulty |
| misleading_* | Integer | Misleading reason flags (10 columns) |
| not_misleading_* | Integer | Not misleading flags (5 columns) |
| trustworthy_sources | Integer | Has trustworthy sources |
| summary | Text | Note summary text |
| is_media_note | Boolean | Is a media note |

### media_metadata table

| Column | Type | Description |
|--------|------|-------------|
| tweet_id | BigInteger | Primary key, foreign key to tweets |
| media_id | String | Media identifier |
| media_type | String | Media type (video/image) |
| title | Text | Media title |
| description | Text | Media description |
| uploader | String | Uploader name |
| uploader_id | String | Uploader ID |
| timestamp | Integer | Unix timestamp |
| duration_ms | Integer | Duration in ms (videos only) |
| like_count | Integer | Number of likes |
| width | Integer | Video/image width |
| height | Integer | Video/image height |
| formats | JSONB | Complete format information |
| local_path | String | Path to downloaded file |

## Migrations

Migrations are managed with Alembic.

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Maintenance

### Backup Database

```bash
pg_dump video_llm_eval > backup.sql
```

### Restore Database

```bash
psql video_llm_eval < backup.sql
```

### Reset Database

```bash
# Drop all tables
alembic downgrade base

# Recreate tables
alembic upgrade head
```

## Troubleshooting

### Connection Issues

If you get connection errors:

1. Check PostgreSQL is running: `pg_ctl status`
2. Verify database exists: `psql -l`
3. Check DATABASE_URL format: `postgresql://user:pass@host:port/dbname`
4. Test connection: `python setup_database.py --check-only`

### Import Issues

If data import fails:

1. Check file paths exist
2. Verify data format matches expected schema
3. Look for foreign key constraint violations
4. Check logs for specific error messages

### Query Performance

For slow queries:

1. Ensure indexes are created (check migration file)
2. Use EXPLAIN ANALYZE to profile queries
3. Consider adding indexes: `CREATE INDEX idx_name ON table(column);`
4. Use pagination for large result sets


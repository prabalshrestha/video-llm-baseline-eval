# Database Import Guide

This guide explains how to import data from CSV exports into your PostgreSQL database.

## Prerequisites

1. **PostgreSQL Database**: Ensure your database is running (locally or in Docker)
2. **Environment Variables**: Set `DATABASE_URL` in your `.env` file:
   ```bash
   DATABASE_URL="postgresql://postgres:password@localhost:5432/video_llm_eval"
   ```
3. **Python Dependencies**: Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Setup Database Schema

Before importing data, set up the database schema:

```bash
python3 setup_database.py
```

This will:
- Check database connection
- Run migrations to create tables
- Verify the setup

## Import Data

### Quick Import (Recommended)

Import all data from the `data/exports/` directory:

```bash
./import_all_data.sh
```

Or specify a custom exports directory:

```bash
./import_all_data.sh /path/to/exports
```

### Manual Import with Options

For more control, use the Python script directly:

```bash
# Import all data
python3 import_from_exports.py

# Import from specific directory
python3 import_from_exports.py --exports-dir /path/to/exports

# Use specific files
python3 import_from_exports.py \
    --tweets-file data/exports/tweets_202601021134.csv \
    --notes-file data/exports/notes_202601021134.csv \
    --media-file data/exports/media_metadata_202601021134.csv

# Skip certain imports
python3 import_from_exports.py --skip-media  # Only import tweets and notes

# Adjust batch size (default: 1000)
python3 import_from_exports.py --batch-size 500
```

## Import Order

The script automatically imports data in the correct order:

1. **Tweets** - Base table (must be imported first)
2. **Notes** - References tweets (foreign key)
3. **Media Metadata** - References tweets (one-to-one relationship)

## Features

### Automatic File Detection

The script automatically finds the latest export files in your exports directory:
- `tweets_*.csv`
- `notes_*.csv`
- `media_metadata_*.csv`

### Upsert (Insert or Update)

The script uses PostgreSQL's `ON CONFLICT` to:
- Insert new records
- Update existing records with same ID
- Prevent duplicate entries

### Progress Tracking

Progress bars show:
- Current batch being processed
- Number of records processed
- Estimated time remaining

### Error Handling

- Invalid data is logged but doesn't stop the import
- Database transactions ensure data consistency
- Detailed error messages help debug issues

## Verify Import

After importing, verify the data:

```bash
python3 setup_database.py --verify
```

This shows:
- Total tweets, notes, and media records
- Engagement statistics
- Classification counts

## Data Format

### Tweets CSV

Expected columns:
- `tweet_id`, `text`, `created_at`
- `author_id`, `author_name`, `author_username`, `author_verified`
- `likes`, `retweets`, `replies`, `quotes`
- `is_verified_video`, `media_type`
- `raw_api_data` (JSON), `api_fetched_at`

### Notes CSV

Expected columns:
- `note_id`, `tweet_id`, `note_author_participant_id`
- `created_at_millis`, `classification`
- `believable`, `harmful`, `validation_difficulty`
- Misleading flags: `misleading_other`, `misleading_factual_error`, etc.
- Not misleading flags: `not_misleading_other`, `not_misleading_factually_correct`, etc.
- `trustworthy_sources`, `summary`, `is_media_note`

### Media Metadata CSV

Expected columns:
- `tweet_id`, `media_id`, `media_type`
- `title`, `description`
- `uploader`, `uploader_id`
- `timestamp`, `duration_ms`, `like_count`
- `width`, `height`
- `formats` (JSON), `local_path`

## Troubleshooting

### Database Connection Issues

```bash
# Check if database is running
docker ps  # If using Docker

# Test connection
python3 setup_database.py --check-only

# Verify DATABASE_URL in .env file
cat .env | grep DATABASE_URL
```

### Missing Export Files

```bash
# List files in exports directory
ls -lh data/exports/

# Check file format
head -2 data/exports/tweets_*.csv
```

### Import Errors

Check the logs for specific error messages. Common issues:
- **Foreign key violations**: Import tweets before notes
- **Data type errors**: Check CSV format (dates, numbers, JSON)
- **Memory issues**: Reduce batch size with `--batch-size 500`

### Duplicate Data

The script uses upsert, so running it multiple times is safe:
- Existing records are updated
- New records are inserted
- No duplicates are created

## Performance Tips

1. **Batch Size**: Larger batches are faster but use more memory
   ```bash
   python3 import_from_exports.py --batch-size 2000
   ```

2. **Partial Imports**: Skip already-imported tables
   ```bash
   python3 import_from_exports.py --skip-tweets --skip-notes
   ```

3. **Database Tuning**: For large imports, temporarily adjust PostgreSQL settings:
   - Increase `shared_buffers`
   - Increase `work_mem`
   - Disable `synchronous_commit` during import

## Remote Server Import

When importing on a remote server:

1. **Transfer export files**:
   ```bash
   rsync -avz data/exports/ user@server:~/video-llm-baseline-eval/data/exports/
   ```

2. **SSH to server and run import**:
   ```bash
   ssh user@server
   cd ~/video-llm-baseline-eval
   source venv/bin/activate
   ./import_all_data.sh
   ```

3. **Verify import**:
   ```bash
   python3 setup_database.py --verify
   ```

## Example Workflow

Complete setup from scratch on remote server:

```bash
# 1. Set up database
python3 setup_database.py

# 2. Import all data
./import_all_data.sh

# 3. Verify import
python3 setup_database.py --verify

# 4. Check specific counts
psql $DATABASE_URL -c "SELECT COUNT(*) FROM tweets;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM notes;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM media_metadata;"
```

## Next Steps

After successful import:
- Use `database/queries.py` for data analysis
- Run evaluations with imported data
- Export updated results as needed


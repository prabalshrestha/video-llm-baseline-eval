# Remote Server Setup Guide

Complete guide for setting up the Video LLM Evaluation database on a remote server with Docker PostgreSQL.

## Server Configuration

Your setup:
- **Server**: `eng402924`
- **Database**: PostgreSQL in Docker container
- **Database Name**: `video_llm_eval`
- **User**: `postgres`
- **Password**: `password`
- **Port**: `5432`

## Step-by-Step Setup

### 1. Ensure PostgreSQL Docker Container is Running

```bash
# Check if container is running
docker ps

# If not running, start it
cd ~/postgres-docker
docker-compose up -d

# Verify it's accessible
docker exec -it <container_name> psql -U postgres -d video_llm_eval -c "SELECT version();"
```

### 2. Set Up Project Environment

```bash
# Navigate to project directory
cd ~/video-llm-baseline-eval

# Activate virtual environment
source venv/bin/activate

# Verify .env file has correct DATABASE_URL
cat .env | grep DATABASE_URL

# Should show:
# DATABASE_URL="postgresql://postgres:password@localhost:5432/video_llm_eval"
```

### 3. Install/Update Dependencies

```bash
# Install python-dotenv (if not already installed)
pip install python-dotenv

# Or install all dependencies
pip install -r requirements.txt
```

### 4. Initialize Database Schema

```bash
# Test database connection
python3 setup_database.py --check-only

# Run migrations to create tables
python3 setup_database.py
```

Expected output:
```
============================================================
Video LLM Evaluation Database Setup
============================================================
Checking database connection...
Database URL: postgresql://postgres:****@localhost:5432/video_llm_eval
✓ Database connection successful
Running database migrations...
✓ Migrations completed successfully
✓ Database setup complete!
```

### 5. Transfer Data Files (From Local Machine)

From your **local machine**, use the sync scripts:

```bash
# Quick sync (exports only - fastest)
./quick_sync.sh

# Sync everything (exports, videos, raw, filtered)
./quick_sync.sh --all

# Or use the advanced sync script
./sync_to_server.sh --dry-run  # Preview first
./sync_to_server.sh            # Then sync

# Manual rsync (alternative)
rsync -avz --progress \
    data/exports/ \
    prabalshrestha@eng402924:~/video-llm-baseline-eval/data/exports/
```

See **[SYNC_GUIDE.md](SYNC_GUIDE.md)** for detailed sync documentation.

### 6. Import Data

Back on the **remote server**:

```bash
# Quick import (recommended)
./import_all_data.sh

# Or with custom options
python3 import_from_exports.py --batch-size 1000
```

Expected output:
```
==================================================
Importing all data from: data/exports
==================================================
Found tweets file: tweets_202601021134.csv
Found notes file: notes_202601021134.csv
Found media_metadata file: media_metadata_202601021134.csv
Checking database connection...
Database connection successful
============================================================
Importing tweets...
Reading tweets from data/exports/tweets_202601021134.csv...
Processing 1234 tweets...
Importing tweets: 100%|██████████| 2/2 [00:01<00:00,  1.23it/s]
Tweets import complete: {'total': 1234, 'inserted': 1234, 'updated': 0, 'errors': 0}
...
```

### 7. Verify Import

```bash
# Run verification script
python3 test_import.py

# Or use setup script
python3 setup_database.py --verify
```

### 8. Query the Database

```bash
# Using psql directly
psql postgresql://postgres:password@localhost:5432/video_llm_eval

# Run queries
SELECT COUNT(*) FROM tweets;
SELECT COUNT(*) FROM notes;
SELECT COUNT(*) FROM media_metadata;

# Exit psql
\q
```

Or use Python:

```python
from database.config import SessionLocal
from database.models import Tweet, Note, MediaMetadata

session = SessionLocal()

# Count records
tweets = session.query(Tweet).count()
notes = session.query(Note).count()
media = session.query(MediaMetadata).count()

print(f"Tweets: {tweets}, Notes: {notes}, Media: {media}")

session.close()
```

## Troubleshooting

### Issue: "Database connection failed: no password supplied"

**Solution**: The `.env` file isn't being loaded. Verify:

```bash
# Check if .env exists
ls -la .env

# Check DATABASE_URL format
cat .env | grep DATABASE_URL

# Should be:
DATABASE_URL="postgresql://postgres:password@localhost:5432/video_llm_eval"

# Manually export as fallback
export DATABASE_URL="postgresql://postgres:password@localhost:5432/video_llm_eval"
python3 setup_database.py --check-only
```

### Issue: "Connection refused"

**Solution**: PostgreSQL container isn't running or not accessible.

```bash
# Check if container is running
docker ps | grep postgres

# Check if port 5432 is listening
netstat -tlnp | grep 5432

# Try connecting with psql
psql postgresql://postgres:password@localhost:5432/video_llm_eval -c "SELECT 1;"

# Check Docker logs
docker logs <container_name>
```

### Issue: "Database does not exist"

**Solution**: Create the database.

```bash
# Connect to PostgreSQL
docker exec -it <container_name> psql -U postgres

# Create database
CREATE DATABASE video_llm_eval;

# Exit
\q
```

### Issue: "Foreign key constraint violation"

**Solution**: Import in correct order (tweets → notes → media).

```bash
# Import tweets first
python3 import_from_exports.py --skip-notes --skip-media

# Then import notes
python3 import_from_exports.py --skip-tweets --skip-media

# Finally import media
python3 import_from_exports.py --skip-tweets --skip-notes
```

### Issue: "Out of memory"

**Solution**: Reduce batch size.

```bash
python3 import_from_exports.py --batch-size 500
```

## Maintenance

### Backup Database

```bash
# Backup to SQL file
docker exec <container_name> pg_dump -U postgres video_llm_eval > backup_$(date +%Y%m%d).sql

# Or use pg_dump directly
pg_dump postgresql://postgres:password@localhost:5432/video_llm_eval > backup.sql
```

### Restore Database

```bash
# Restore from SQL file
docker exec -i <container_name> psql -U postgres video_llm_eval < backup.sql

# Or use psql directly
psql postgresql://postgres:password@localhost:5432/video_llm_eval < backup.sql
```

### Re-import Data

```bash
# Clear existing data
psql postgresql://postgres:password@localhost:5432/video_llm_eval -c "TRUNCATE tweets CASCADE;"

# Re-import
./import_all_data.sh
```

### Update Schema

```bash
# After model changes, create migration
alembic revision --autogenerate -m "Description of changes"

# Apply migration
alembic upgrade head
```

## Performance Optimization

For large datasets, optimize PostgreSQL:

```bash
# Connect to database
psql postgresql://postgres:password@localhost:5432/video_llm_eval

-- Increase work memory for import
ALTER DATABASE video_llm_eval SET work_mem = '256MB';

-- Disable synchronous commit during import (faster but less safe)
ALTER DATABASE video_llm_eval SET synchronous_commit = 'off';

-- Re-enable after import
ALTER DATABASE video_llm_eval SET synchronous_commit = 'on';

-- Analyze tables after import
ANALYZE tweets;
ANALYZE notes;
ANALYZE media_metadata;
```

## Monitoring

### Check Database Size

```bash
psql postgresql://postgres:password@localhost:5432/video_llm_eval -c "
SELECT 
    pg_size_pretty(pg_database_size('video_llm_eval')) as db_size;
"
```

### Check Table Sizes

```bash
psql postgresql://postgres:password@localhost:5432/video_llm_eval -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### Check Active Connections

```bash
psql postgresql://postgres:password@localhost:5432/video_llm_eval -c "
SELECT count(*) FROM pg_stat_activity WHERE datname = 'video_llm_eval';
"
```

## Quick Reference

### Common Commands

```bash
# Check connection
python3 setup_database.py --check-only

# Run migrations
python3 setup_database.py --migrate-only

# Import all data
./import_all_data.sh

# Verify data
python3 test_import.py

# Get statistics
python3 setup_database.py --verify
```

### Environment Variables

Required in `.env` file:

```bash
DATABASE_URL="postgresql://postgres:password@localhost:5432/video_llm_eval"
TWITTER_BEARER_TOKEN="your_token_here"
OPENAI_API_KEY="your_key_here"
```

### File Locations

- **Database config**: `database/config.py`
- **Models**: `database/models.py`
- **Import script**: `import_from_exports.py`
- **Test script**: `test_import.py`
- **Setup script**: `setup_database.py`
- **Export files**: `data/exports/`
- **Migrations**: `database/migrations/versions/`

## Next Steps

After successful setup:

1. **Run evaluations**: Use the imported data for Video LLM evaluations
2. **Query data**: Use `database/queries.py` for analysis
3. **Export results**: Generate new exports as needed
4. **Monitor performance**: Check database size and query performance
5. **Schedule backups**: Set up regular database backups

## Support

If you encounter issues:

1. Check logs in terminal output
2. Review `DATABASE_IMPORT.md` for detailed troubleshooting
3. Verify Docker container is running: `docker ps`
4. Test database connection: `python3 setup_database.py --check-only`
5. Check `.env` file format and values


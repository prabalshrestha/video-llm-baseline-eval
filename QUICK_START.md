# Quick Start: Database Import

**TL;DR**: Import your CSV exports into PostgreSQL in 3 commands.

## Prerequisites

- PostgreSQL running (Docker or local)
- `.env` file with `DATABASE_URL` set
- CSV export files in `data/exports/`

## Three-Step Setup

### 1. Setup Database

```bash
python3 setup_database.py
```

### 2. Import Data

```bash
./import_all_data.sh
```

### 3. Verify

```bash
python3 test_import.py
```

## Done! 🎉

Your database now contains:

- Tweets with engagement metrics
- Community Notes with classifications
- Media metadata from yt-dlp

## What Was Created

### New Files

1. **`import_from_exports.py`** - Main import script

   - Reads CSV files from `data/exports/`
   - Handles data type conversions
   - Uses bulk upserts for efficiency
   - Shows progress bars

2. **`import_all_data.sh`** - Quick wrapper script

   - Activates venv
   - Runs import with defaults
   - Shows summary

3. **`test_import.py`** - Verification script

   - Counts records
   - Checks relationships
   - Shows data quality stats

4. **`DATABASE_IMPORT.md`** - Detailed documentation

   - All import options
   - Troubleshooting guide
   - Performance tips

5. **`REMOTE_SERVER_SETUP.md`** - Server-specific guide
   - Step-by-step for your eng402924 server
   - Docker PostgreSQL setup
   - Common issues and solutions

### Modified Files

1. **`database/config.py`** - Now loads `.env` automatically
   - Added `python-dotenv` support
   - Automatic environment variable loading

## Import Options

### Basic Usage

```bash
# Import everything
./import_all_data.sh

# Or with Python directly
python3 import_from_exports.py
```

### Advanced Usage

```bash
# Custom directory
python3 import_from_exports.py --exports-dir /path/to/exports

# Specific files
python3 import_from_exports.py \
    --tweets-file data/exports/tweets_202601021134.csv \
    --notes-file data/exports/notes_202601021134.csv \
    --media-file data/exports/media_metadata_202601021134.csv

# Skip certain tables
python3 import_from_exports.py --skip-media

# Adjust performance
python3 import_from_exports.py --batch-size 2000
```

## Verify Import

```bash
# Quick verification
python3 test_import.py

# Detailed statistics
python3 setup_database.py --verify

# Direct SQL query
psql $DATABASE_URL -c "SELECT COUNT(*) FROM tweets;"
```

## Troubleshooting

### "Database connection failed"

```bash
# Check .env file
cat .env | grep DATABASE_URL

# Test connection
python3 setup_database.py --check-only

# Manual export (fallback)
export DATABASE_URL="postgresql://postgres:password@localhost:5432/video_llm_eval"
```

### "No export files found"

```bash
# Check files exist
ls -lh data/exports/

# Specify files manually
python3 import_from_exports.py --tweets-file data/exports/tweets_*.csv
```

### "Foreign key constraint violation"

Import order matters! Script handles this automatically, but if you see errors:

```bash
# Import in correct order
python3 import_from_exports.py --skip-notes --skip-media  # Tweets first
python3 import_from_exports.py --skip-tweets --skip-media  # Notes second
python3 import_from_exports.py --skip-tweets --skip-notes  # Media last
```

## Remote Server

Transfer data and import on your remote server (eng402924):

```bash
# 1. Sync data from local machine
./quick_sync.sh              # Exports only (fast)
# or
./quick_sync.sh --all        # Everything

# 2. SSH to server
ssh prabalshrestha@eng402924

# 3. Run import
cd ~/video-llm-baseline-eval
./import_all_data.sh

# 4. Verify
python3 test_import.py
```

See:

- **[SYNC_GUIDE.md](SYNC_GUIDE.md)** for sync options
- **[REMOTE_SERVER_SETUP.md](REMOTE_SERVER_SETUP.md)** for detailed server setup

## Features

✅ **Automatic file detection** - Finds latest exports  
✅ **Upsert support** - Safe to run multiple times  
✅ **Progress tracking** - Shows real-time progress  
✅ **Error handling** - Continues on errors, logs details  
✅ **Batch processing** - Efficient bulk inserts  
✅ **Data validation** - Type checking and conversions  
✅ **Foreign key handling** - Correct import order

## Next Steps

After successful import:

1. **Query your data**:

   ```python
   from database.config import SessionLocal
   from database.models import Tweet, Note

   session = SessionLocal()
   tweets = session.query(Tweet).filter(Tweet.likes > 1000).all()
   ```

2. **Run analysis**: Use `database/queries.py`

3. **Start evaluations**: Your data is ready for Video LLM testing

4. **Export results**: Generate new exports as needed

## Documentation

- **Quick Start**: `QUICK_START.md` (this file)
- **Detailed Import Guide**: `DATABASE_IMPORT.md`
- **Remote Server Setup**: `REMOTE_SERVER_SETUP.md`
- **Database Schema**: `database/models.py`
- **Setup Script**: `setup_database.py --help`
- **Import Script**: `python3 import_from_exports.py --help`

## Help

```bash
# Import script help
python3 import_from_exports.py --help

# Setup script help
python3 setup_database.py --help

# Check what's in database
python3 test_import.py
```

---

**Questions?** Check the detailed guides or review the error logs.

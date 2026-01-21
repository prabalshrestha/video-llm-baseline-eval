# Video File Naming and Database Migration Guide

This guide explains how to migrate from the old video naming convention to the new one, and update the database schema to support multiple videos per tweet.

## Overview

### Old Format
- **Naming**: `video_001_1234567890.mp4` (arbitrary index + tweet ID)
- **Problem**: Multiple download sessions created duplicate indexes, causing mismatches
- **Schema**: One-to-one relationship (one video per tweet)

### New Format
- **Naming**: `1234567890_1.mp4` (tweet ID + video index)
- **Benefits**: Clear identification, supports multiple videos per tweet
- **Schema**: One-to-many relationship (multiple videos per tweet possible)

## Migration Steps

### Step 1: Backup Your Data

```bash
# Backup database
pg_dump video_llm_eval > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup video files (optional but recommended)
tar -czf videos_backup_$(date +%Y%m%d_%H%M%S).tar.gz data/videos/
```

### Step 2: Run the Mapping Fix Script (DRY RUN)

First, do a dry run to see what changes will be made:

```bash
python fix_video_mapping.py --dry-run
```

Review the output carefully. It will show:
- Which files will be renamed
- How many tweets have multiple videos
- Any potential issues

### Step 3: Apply the Mapping Fix

If the dry run looks good, apply the changes:

```bash
python fix_video_mapping.py
```

This script will:
1. ✅ Rename all video files to new format (`TWEETID_1.mp4`)
2. ✅ Rename associated `.info.json` files
3. ✅ Update `MediaMetadata.local_path` in database
4. ✅ Verify all mappings are correct

**Expected Output:**
```
Starting video mapping fix...
Mode: LIVE
Scanning video directory: data/videos
Found 445 video files
Grouped into 445 unique tweets

Renaming video files...
✓ Renamed: video_001_1756422035629121538.mp4 -> 1756422035629121538_1.mp4
✓ Renamed: video_002_1771221581278126080.mp4 -> 1771221581278126080_1.mp4
...

Updating database...
✓ Updated DB: 1756422035629121538
✓ Updated DB: 1771221581278126080
...

Verifying database mappings...
✓ Correct: 445
✗ Incorrect: 0

SUMMARY
============================================================
Total video files found: 445
Files renamed: 445
Files skipped: 0
Rename errors: 0
Database records updated: 445
Database update errors: 0
============================================================
```

### Step 4: Run Database Migration

After files are renamed and database is updated, run the schema migration:

```bash
# Run migration to add media_key and video_index columns
alembic upgrade head
```

This migration will:
1. Add `media_key` column (primary key)
2. Add `video_index` column (for ordering)
3. Populate columns for existing records
4. Update primary key and indexes
5. Add unique constraint on `(tweet_id, video_index)`

### Step 5: Verify Everything Works

```bash
# Test dataset creation
python scripts/data_processing/create_dataset.py --sample-size 10

# Verify video paths in dataset
python -c "
import json
from pathlib import Path

with open('data/evaluation/dataset.json') as f:
    dataset = json.load(f)

print(f'Total samples: {len(dataset[\"samples\"])}')
for sample in dataset['samples'][:5]:
    video_path = sample['video']['path']
    filename = Path(video_path).name
    tweet_id = sample['tweet']['tweet_id']
    print(f'Tweet: {tweet_id} | Video: {filename}')
    
    # Verify filename format
    if filename.startswith(tweet_id):
        print('  ✓ Correct format')
    else:
        print('  ✗ MISMATCH!')
"
```

## Database Schema Changes

### MediaMetadata Table Updates

**Before:**
```python
class MediaMetadata(Base):
    tweet_id = Column(BigInteger, primary_key=True)  # One-to-one
    media_id = Column(String(255))
    local_path = Column(String(500))
    # ... other columns
```

**After:**
```python
class MediaMetadata(Base):
    media_key = Column(String(255), primary_key=True)  # New primary key
    tweet_id = Column(BigInteger, ForeignKey(...))     # Foreign key (one-to-many)
    video_index = Column(Integer, default=1)           # Video sequence number
    media_id = Column(String(255))
    local_path = Column(String(500))
    # ... other columns
```

### Key Changes:
- **Primary Key**: Changed from `tweet_id` to `media_key`
- **media_key**: Format is `{tweet_id}_{video_index}` (e.g., `1234567890_1`)
- **video_index**: Sequence number (1, 2, 3...) for videos in same tweet
- **Relationship**: Tweet → MediaMetadata is now one-to-many
- **Unique Constraint**: `(tweet_id, video_index)` must be unique

## File Naming Convention

### Format
```
{tweet_id}_{video_index}.{extension}
```

### Examples
```
1234567890_1.mp4      # First video from tweet 1234567890
1234567890_2.mp4      # Second video from same tweet
9876543210_1.webm     # First video from tweet 9876543210
```

### Metadata Files
```
1234567890_1.info.json  # Metadata for first video
1234567890_2.info.json  # Metadata for second video
```

## Code Changes

### 1. Download Script (`download_videos.py`)

**Before:**
```python
output_template = str(self.videos_dir / f"video_{index:03d}_%(id)s.%(ext)s")
```

**After:**
```python
output_template = str(self.videos_dir / f"{tweet_id}_{video_index}.%(ext)s")
```

### 2. Dataset Creation (`create_dataset.py`)

The script now needs to handle the new relationship:

```python
# Query tweets with their videos (now one-to-many)
query = (
    session.query(Tweet, MediaMetadata)
    .join(MediaMetadata, Tweet.tweet_id == MediaMetadata.tweet_id)
    .filter(MediaMetadata.local_path.isnot(None))
    .order_by(Tweet.tweet_id, MediaMetadata.video_index)  # Order by video_index
)
```

## Handling Multiple Videos Per Tweet

### In Future Downloads

When a tweet has multiple videos, they'll be downloaded as:
```
1234567890_1.mp4
1234567890_2.mp4
1234567890_3.mp4
```

### In Database

```python
# Create records for multiple videos
media1 = MediaMetadata(
    media_key="1234567890_1",
    tweet_id=1234567890,
    video_index=1,
    local_path="/path/to/1234567890_1.mp4"
)

media2 = MediaMetadata(
    media_key="1234567890_2",
    tweet_id=1234567890,
    video_index=2,
    local_path="/path/to/1234567890_2.mp4"
)
```

### In Dataset

For evaluation, you'll typically use the first video:
```python
# Get first video for a tweet
media = session.query(MediaMetadata).filter_by(
    tweet_id=tweet_id,
    video_index=1
).first()
```

Or get all videos:
```python
# Get all videos for a tweet
all_videos = session.query(MediaMetadata).filter_by(
    tweet_id=tweet_id
).order_by(MediaMetadata.video_index).all()
```

## Rollback Instructions

If something goes wrong, you can rollback:

### Rollback Database Migration
```bash
# Downgrade to previous schema (WARNING: deletes videos with index > 1)
alembic downgrade -1
```

### Restore from Backup
```bash
# Restore database
psql video_llm_eval < backup_YYYYMMDD_HHMMSS.sql

# Restore video files
rm -rf data/videos/*
tar -xzf videos_backup_YYYYMMDD_HHMMSS.tar.gz
```

## Troubleshooting

### Issue: Files already exist error
**Solution**: Some files may already be in the correct format. The script will skip them.

### Issue: Database connection error
**Solution**: Make sure PostgreSQL is running and DATABASE_URL is set correctly in `.env`

### Issue: Permission denied
**Solution**: Check file permissions on `data/videos/` directory

### Issue: Mismatch after migration
**Solution**: Run the verification step:
```bash
python fix_video_mapping.py --dry-run
```

Then check the output for specific mismatches.

## Post-Migration Checklist

- [ ] All video files renamed to new format
- [ ] Database `local_path` updated for all videos
- [ ] Database migration completed successfully
- [ ] No mismatches in verification step
- [ ] Dataset creation works without errors
- [ ] Evaluation runs successfully with new paths
- [ ] Backup files can be deleted (after confirming everything works)

## Benefits of New System

1. **Clear Identification**: Tweet ID is in filename, making debugging easier
2. **No Duplicates**: Tweet ID-based naming prevents conflicts
3. **Multiple Videos**: Schema supports tweets with multiple videos
4. **Consistent Ordering**: `video_index` maintains video order
5. **Better Tracking**: `media_key` provides unique identifier for each video
6. **Easier Recovery**: Can rebuild mappings from filenames alone

## Questions?

If you encounter issues during migration:
1. Check the logs carefully
2. Run dry-run mode to preview changes
3. Make sure backups are in place
4. Verify database connectivity before starting

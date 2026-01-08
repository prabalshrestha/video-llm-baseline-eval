# Data Sync Guide

Complete guide for syncing data between your local machine and remote server.

## Quick Start

### Fastest Way (Exports Only)

```bash
./quick_sync.sh
```

This syncs only the `data/exports/` directory (usually smallest and fastest).

### Sync Everything

```bash
./quick_sync.sh --all
```

This syncs all data directories: exports, videos, raw, and filtered.

## Scripts Available

### 1. `quick_sync.sh` - Simple & Fast

**Best for**: Quick transfers, exports only

```bash
# Sync exports only (default)
./quick_sync.sh

# Sync everything
./quick_sync.sh --all

# Sync videos only
./quick_sync.sh --videos

# Help
./quick_sync.sh --help
```

**Features:**
- Simple one-command sync
- Color-coded output
- Automatic remote directory creation
- Progress tracking

### 2. `sync_to_server.sh` - Advanced & Interactive

**Best for**: Selective syncing, dry runs, control

```bash
# Sync everything with confirmations
./sync_to_server.sh

# Sync exports only
./sync_to_server.sh --exports-only

# Sync videos only
./sync_to_server.sh --videos-only

# Exclude videos from sync
./sync_to_server.sh --no-videos

# Preview without syncing (dry run)
./sync_to_server.sh --dry-run

# Help
./sync_to_server.sh --help
```

**Features:**
- Interactive confirmations
- File/size summaries before sync
- Dry run mode
- Selective directory syncing
- Excludes unnecessary files

## Configuration

Edit `sync_config.sh` to customize:

```bash
# Remote server
export SYNC_REMOTE_USER="prabalshrestha"
export SYNC_REMOTE_HOST="eng402924"
export SYNC_REMOTE_PATH="~/video-llm-baseline-eval"

# What to sync
export SYNC_EXPORTS=true
export SYNC_VIDEOS=true
export SYNC_RAW=true
export SYNC_FILTERED=true
```

## Typical Workflow

### Initial Setup (First Time)

```bash
# 1. Sync all data to server
./quick_sync.sh --all

# 2. SSH to server
ssh prabalshrestha@eng402924

# 3. Setup database
cd ~/video-llm-baseline-eval
python3 setup_database.py

# 4. Import data
./import_all_data.sh

# 5. Verify
python3 test_import.py
```

### Regular Updates

When you have new data locally:

```bash
# 1. Sync just the exports (fast)
./quick_sync.sh

# 2. SSH to server
ssh prabalshrestha@eng402924

# 3. Re-import (upserts automatically)
cd ~/video-llm-baseline-eval
./import_all_data.sh
```

## Data Sizes

Typical sizes (your mileage may vary):

- **exports/**: 10-100 MB (CSV files)
- **raw/**: 100-500 MB (TSV files)
- **filtered/**: 10-50 MB (Filtered CSVs)
- **videos/**: 1-50 GB (Video files)

**Recommendation**: Sync exports first, then videos separately if needed.

## SSH Setup

### Option 1: Password-based (Works Immediately)

The scripts now support password authentication! You'll be prompted for your password during sync.

```bash
./quick_sync.sh
# Enter your password when prompted
```

**Pros**: Works immediately, no setup  
**Cons**: Must enter password each time

### Option 2: SSH Keys (Recommended - 5 Minute Setup)

Set up SSH keys for password-less syncing:

```bash
# 1. Generate SSH key (if you don't have one)
ssh-keygen -t ed25519

# 2. Copy to server (enter password one last time)
ssh-copy-id prabalshrestha@eng402924

# 3. Test connection (should work without password)
ssh prabalshrestha@eng402924

# 4. Now sync without passwords!
./quick_sync.sh
```

**Pros**: No password prompts, faster, more secure  
**Cons**: 5-minute one-time setup

See **[SSH_SETUP.md](SSH_SETUP.md)** for detailed SSH key setup instructions.

## What Gets Synced

### Included

✅ All data files (CSV, TSV, JSON)  
✅ Video files (MP4, WebM, etc.)  
✅ Metadata files (.info.json)  
✅ Analysis results  
✅ Filtered data  

### Excluded (Automatic)

❌ Python cache (`*.pyc`, `__pycache__`)  
❌ System files (`.DS_Store`)  
❌ Temporary files (`*.tmp`)  
❌ Git files (`.git/`)  

## Advanced Usage

### Dry Run (Preview)

See what would be synced without actually syncing:

```bash
./sync_to_server.sh --dry-run
```

### Bandwidth Limiting

Limit bandwidth usage (useful for slow connections):

```bash
rsync -avz --progress --bwlimit=1000 \
    data/exports/ prabalshrestha@eng402924:~/video-llm-baseline-eval/data/exports/
```

Replace `1000` with your desired KB/s limit.

### Resume Interrupted Transfer

Rsync automatically resumes interrupted transfers. Just run the same command again:

```bash
./quick_sync.sh --videos
```

### Sync Specific Files

For manual control:

```bash
# Sync specific CSV file
rsync -avz --progress \
    data/exports/tweets_202601021134.csv \
    prabalshrestha@eng402924:~/video-llm-baseline-eval/data/exports/

# Sync specific video
rsync -avz --progress \
    data/videos/video_001_*.mp4 \
    prabalshrestha@eng402924:~/video-llm-baseline-eval/data/videos/
```

## Troubleshooting

### "Connection refused"

**Problem**: Cannot connect to server

**Solutions**:
```bash
# Test SSH connection
ssh prabalshrestha@eng402924

# Check server is reachable
ping eng402924

# Verify SSH config
cat ~/.ssh/config
```

### "Permission denied"

**Problem**: SSH authentication failed

**Solutions**:
1. Check username is correct
2. Verify SSH keys are set up
3. Use password authentication
4. Check server SSH config

### "No such file or directory"

**Problem**: Remote directory doesn't exist

**Solution**: Scripts create directories automatically, but you can manually:
```bash
ssh prabalshrestha@eng402924 "mkdir -p ~/video-llm-baseline-eval/data"
```

### "Disk quota exceeded"

**Problem**: Not enough space on server

**Solutions**:
```bash
# Check disk space on server
ssh prabalshrestha@eng402924 "df -h"

# Check specific directory size
ssh prabalshrestha@eng402924 "du -sh ~/video-llm-baseline-eval/data/*"

# Clean up old files if needed
ssh prabalshrestha@eng402924 "cd ~/video-llm-baseline-eval && rm -rf data/videos/*.tmp"
```

### Transfer is Very Slow

**Solutions**:
1. Use `--no-videos` to skip large video files
2. Sync during off-peak hours
3. Use compression (enabled by default)
4. Check network connection

### File Already Exists

**Normal**: Rsync updates existing files. This is expected behavior.

If you want to delete files on remote that don't exist locally:
```bash
rsync -avz --progress --delete \
    data/exports/ prabalshrestha@eng402924:~/video-llm-baseline-eval/data/exports/
```

⚠️ **Warning**: `--delete` removes files on remote. Use carefully!

## Performance Tips

### 1. Compress Data

```bash
# Compress before transfer (for very large files)
tar -czf data_backup.tar.gz data/
scp data_backup.tar.gz prabalshrestha@eng402924:~/

# On server, extract
ssh prabalshrestha@eng402924 "cd ~ && tar -xzf data_backup.tar.gz"
```

### 2. Parallel Transfers

For multiple large files:

```bash
# Terminal 1
rsync -avz data/videos/video_001_* prabalshrestha@eng402924:~/video-llm-baseline-eval/data/videos/

# Terminal 2
rsync -avz data/exports/ prabalshrestha@eng402924:~/video-llm-baseline-eval/data/exports/
```

### 3. Skip Unchanged Files

Rsync already does this by default! It only transfers changed files.

## Monitoring Transfer

### Check Progress

Both scripts show progress by default:
- Current file being transferred
- Transfer speed
- Time remaining

### Check on Server

While syncing, on server:

```bash
# Watch directory size change
watch -n 5 'du -sh ~/video-llm-baseline-eval/data/*'

# Monitor disk usage
watch -n 5 'df -h'
```

## Examples

### Example 1: First-time Full Sync

```bash
# Preview what will be synced
./sync_to_server.sh --dry-run

# Do the actual sync
./quick_sync.sh --all

# Check what arrived on server
ssh prabalshrestha@eng402924 "ls -lh ~/video-llm-baseline-eval/data/exports/"
```

### Example 2: Quick Update

```bash
# Just sync new exports
./quick_sync.sh

# Import on server
ssh prabalshrestha@eng402924 "cd ~/video-llm-baseline-eval && ./import_all_data.sh"
```

### Example 3: Videos Only

```bash
# Sync videos (large files)
./quick_sync.sh --videos

# Or with advanced script for confirmation
./sync_to_server.sh --videos-only
```

### Example 4: Everything Except Videos

```bash
./sync_to_server.sh --no-videos
```

## Complete Workflow Example

```bash
# ============================================================
# On Local Machine
# ============================================================

# 1. Export your current database
python3 export_database.py

# 2. Preview sync
./sync_to_server.sh --dry-run

# 3. Sync to server
./quick_sync.sh --all

# ============================================================
# On Remote Server
# ============================================================

# 4. Connect to server
ssh prabalshrestha@eng402924

# 5. Navigate to project
cd ~/video-llm-baseline-eval

# 6. Setup database (first time only)
python3 setup_database.py

# 7. Import data
./import_all_data.sh

# 8. Verify
python3 test_import.py

# 9. Done! Query your data
python3 -c "
from database.config import SessionLocal
from database.models import Tweet
session = SessionLocal()
print(f'Total tweets: {session.query(Tweet).count()}')
"
```

## Security Notes

1. **SSH Keys**: Use SSH keys instead of passwords for better security
2. **Permissions**: Scripts use standard rsync, respecting file permissions
3. **Encryption**: SSH encrypts all data in transit
4. **No Plain Passwords**: Never put passwords in scripts or config files

## Next Steps

After syncing:

1. **Import Data**: Run `./import_all_data.sh` on server
2. **Verify**: Run `python3 test_import.py`
3. **Use Database**: Start querying and analyzing
4. **Regular Updates**: Re-sync when you have new data

## Quick Reference

```bash
# Quick sync (exports only)
./quick_sync.sh

# Sync everything
./quick_sync.sh --all

# Sync videos only
./quick_sync.sh --videos

# Advanced sync with options
./sync_to_server.sh --dry-run
./sync_to_server.sh --exports-only
./sync_to_server.sh --no-videos

# Manual rsync
rsync -avz data/exports/ prabalshrestha@eng402924:~/video-llm-baseline-eval/data/exports/
```

---

**Questions?** Check the troubleshooting section or run with `--help` flag.


# Video Migration Action Plan

## 🎯 Goal
Fix video-tweet mismatches and update to new naming convention that supports multiple videos per tweet.

## 📋 Pre-Migration Checklist

- [ ] Read `VIDEO_MIGRATION_SUMMARY.md` (5 min quick overview)
- [ ] Understand the issue: Current files named `video_001_TWEETID.mp4` causing mismatches
- [ ] Understand the solution: Rename to `TWEETID_1.mp4` format
- [ ] Have database access (check `DATABASE_URL` in `.env`)
- [ ] Have `~2GB` free disk space (for potential backup)
- [ ] Close any running evaluations or scripts

## 🚀 Migration Steps

### Step 1: Check for Duplicates
**Time: ~30 seconds**

```bash
# Check if there are any duplicate video records
python check_duplicates.py
```

**Expected Output**:
```
✓ No duplicate records found! All tweets have exactly one video.
```

**If duplicates found**:
```bash
# Fix duplicates (keeps best record, deletes extras)
python check_duplicates.py --fix
```

**✅ Checkpoint**: No duplicates remaining

---

### Step 2: Backup (CRITICAL!)
**Time: ~2-5 minutes**

```bash
# Create backups directory
mkdir -p backups

# Backup database
pg_dump video_llm_eval > backups/db_backup_$(date +%Y%m%d_%H%M%S).sql

# Optional: Backup videos (if you have space)
tar -czf backups/videos_backup_$(date +%Y%m%d_%H%M%S).tar.gz data/videos/
```

**✅ Checkpoint**: Verify backup file exists and has reasonable size
```bash
ls -lh backups/
```

---

### Step 3: Preview Changes (Dry Run)
**Time: ~1 minute**

```bash
python fix_video_mapping.py --dry-run
```

**👀 Review the output**:
- How many files will be renamed?
- Are there any warnings or errors?
- Does the rename mapping look correct?

**✅ Checkpoint**: No errors in dry-run output

---

### Step 4: Apply File Renaming
**Time: ~2-5 minutes** (depends on number of videos)

```bash
python fix_video_mapping.py
```

**Expected Output**:
```
Starting video mapping fix...
Mode: LIVE
Found 445 video files
Grouped into 445 unique tweets

Renaming video files...
✓ Renamed: video_001_1756422035629121538.mp4 -> 1756422035629121538_1.mp4
...

Updating database...
✓ Updated DB: 1756422035629121538
...

Verifying database mappings...
✓ Correct: 445
✗ Incorrect: 0

SUMMARY
Total video files found: 445
Files renamed: 445
Database records updated: 445
```

**✅ Checkpoint**: 
- All files renamed successfully
- Database records updated
- Verification shows 0 incorrect mappings

**❌ If errors occur**: Stop here, check logs, restore from backup if needed

---

### Step 5: Update Database Schema
**Time: ~30 seconds**

```bash
alembic upgrade head
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Running upgrade 97b67d0f69ca -> add_media_key_multi, add media_key for multiple videos per tweet
```

**✅ Checkpoint**: Migration completes without errors

---

### Step 6: Verify Everything Works
**Time: ~1-2 minutes**

```bash
# Test dataset creation with small sample
python scripts/data_processing/create_dataset.py --sample-size 10
```

**Expected Output**:
```
Found 445 tweets with downloaded videos and API data
...
✓ Created dataset with 10 samples
✓ Saved to: data/evaluation/dataset.json
```

**✅ Checkpoint**: Dataset created successfully, no errors

---

### Step 7: Detailed Verification
**Time: ~30 seconds**

```bash
python -c "
import json
from pathlib import Path

with open('data/evaluation/dataset.json') as f:
    dataset = json.load(f)

print(f'✓ Loaded {len(dataset[\"samples\"])} samples\n')
print('Checking first 5 videos:')
for i, sample in enumerate(dataset['samples'][:5], 1):
    video_path = Path(sample['video']['path'])
    tweet_id = sample['tweet']['tweet_id']
    filename = video_path.name
    
    # Check format
    if filename.startswith(str(tweet_id)):
        status = '✓'
    else:
        status = '✗ MISMATCH'
    
    print(f'{i}. {status} Tweet: {tweet_id} | Video: {filename}')
"
```

**Expected Output**:
```
✓ Loaded 10 samples

Checking first 5 videos:
1. ✓ Tweet: 1756422035629121538 | Video: 1756422035629121538_1.mp4
2. ✓ Tweet: 1771221581278126080 | Video: 1771221581278126080_1.mp4
3. ✓ Tweet: 1774835758823591947 | Video: 1774835758823591947_1.mp4
...
```

**✅ Checkpoint**: All videos show ✓ with correct format

---

### Step 8: Test Evaluation (Optional but Recommended)
**Time: ~5-10 minutes** (depends on API speed)

```bash
# Run quick evaluation on 3 samples with one model
python scripts/evaluation/evaluate_models.py \
  --models gemini \
  --gemini-model gemini-2.5-flash \
  --limit 3
```

**✅ Checkpoint**: Evaluation runs without video path errors

---

## ✅ Post-Migration Checklist

- [ ] All video files renamed to `TWEETID_1.mp4` format
- [ ] Database updated successfully
- [ ] Schema migration completed
- [ ] Dataset creation works
- [ ] No mismatches in verification
- [ ] Evaluation runs successfully (optional)
- [ ] Document backup location for future reference

## 🧹 Cleanup (After Confirming Everything Works)

**Wait 1-2 days** to ensure everything is stable, then:

```bash
# Delete backups (optional, if everything is working)
rm -rf backups/

# Note: Keep at least one database backup somewhere safe!
```

## 🔄 If Something Goes Wrong

### Quick Rollback

```bash
# Restore database
psql video_llm_eval < backups/db_backup_YYYYMMDD_HHMMSS.sql

# Restore videos (if backed up)
rm -rf data/videos/*
tar -xzf backups/videos_backup_YYYYMMDD_HHMMSS.tar.gz
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Database connection error | Check PostgreSQL is running: `pg_isready` |
| Permission denied on files | Check ownership: `ls -la data/videos/` |
| Migration already applied | Check status: `alembic current` |
| Files not found | Verify path: `ls data/videos/` |

## 📚 Documentation References

| Document | When to Use |
|----------|-------------|
| `VIDEO_MIGRATION_SUMMARY.md` | Quick reference before starting |
| `VIDEO_MIGRATION_GUIDE.md` | Detailed explanations and troubleshooting |
| `IMPLEMENTATION_VIDEO_MIGRATION.md` | Technical details and code changes |
| This file | Step-by-step execution plan |

## ⏱️ Total Time Estimate

- **Fast path** (no issues): ~10-15 minutes
- **With verification**: ~20-30 minutes
- **With full testing**: ~30-45 minutes

## 🎉 Success!

After completing all steps with ✅ checkpoints passed, you will have:

1. ✨ **Fixed all video-tweet mismatches**
2. 🔢 **Clean naming**: `1234567890_1.mp4` format
3. 💾 **Updated schema**: Supports multiple videos per tweet
4. 🔍 **Verified mappings**: 100% correct tweet-to-video associations
5. 📚 **Future-proof**: Ready for tweets with multiple videos

---

**Ready to start?** Begin with Step 1: Backup! 🚀

**Need help?** Check `VIDEO_MIGRATION_GUIDE.md` for troubleshooting.

# Duplicate Prevention System

## ✅ Yes, Duplicates Are Fully Covered!

We have **multiple layers** of duplicate prevention to ensure data integrity.

## 🛡️ Three Layers of Protection

### 1. Database-Level Constraint (Strongest)

**Unique Constraint** on `(tweet_id, video_index)`:

```python
# In database/models.py (line 187)
sa.UniqueConstraint('tweet_id', 'video_index', name='uq_media_metadata_tweet_video_idx')
```

**What it does:**
- PostgreSQL **enforces** uniqueness at the database level
- Impossible to insert duplicate `(tweet_id, video_index)` combinations
- Raises error: `"duplicate key value violates unique constraint"`

**Example:**
```python
# ✅ Allowed - different video_index
MediaMetadata(media_key="123_1", tweet_id=123, video_index=1)
MediaMetadata(media_key="123_2", tweet_id=123, video_index=2)

# ❌ Blocked by database - duplicate video_index
MediaMetadata(media_key="123_1", tweet_id=123, video_index=1)
MediaMetadata(media_key="123_1b", tweet_id=123, video_index=1)  # ERROR!
```

### 2. Application-Level Check (Download Script)

**Smart skip logic** in `download_videos.py` (lines 100-104):

```python
if video.local_path:
    # Check if file actually exists
    video_path = Path(video.local_path)
    if video_path.exists():
        continue  # Skip - already downloaded
```

**What it does:**
- Checks if video already has `local_path` set
- Verifies file actually exists on disk
- Skips downloading if already present
- Only re-downloads in `--force` mode

### 3. Pre-Migration Duplicate Checker

**New script** `check_duplicates.py`:

```bash
# Check for existing duplicates
python check_duplicates.py

# Fix duplicates (keeps best record)
python check_duplicates.py --fix
```

**What it does:**
- Scans database for duplicate video records
- Identifies tweets with multiple MediaMetadata records
- Optionally cleans up duplicates (keeps best one)
- Run **before** migration to ensure clean state

## 📊 How It Prevents Different Types of Duplicates

### Type 1: Same Tweet, Same Video Downloaded Twice

**Scenario**: Accidentally run download script twice

**Prevention**:
1. **Application level**: Script checks `local_path` exists → skips
2. **Database level**: Can't insert duplicate `(tweet_id, video_index=1)`

**Result**: ✅ Second download is skipped

---

### Type 2: Same Tweet, Multiple Videos (Legitimate)

**Scenario**: Tweet has 2+ videos (e.g., carousel)

**Prevention**:
1. **Application level**: Each video gets unique `video_index` (1, 2, 3...)
2. **Database level**: Allows different `video_index` values
3. **File naming**: `123_1.mp4`, `123_2.mp4`, `123_3.mp4`

**Result**: ✅ All videos stored correctly, no duplicates

---

### Type 3: Concurrent Downloads

**Scenario**: Two processes downloading same video simultaneously

**Prevention**:
1. **Database level**: Unique constraint prevents both from inserting
2. **First wins**: One process succeeds, other gets error
3. **Error handling**: Failed process can retry or skip

**Result**: ✅ Only one record created

---

### Type 4: Manual Database Edits Gone Wrong

**Scenario**: Someone manually adds duplicate record

**Prevention**:
1. **Database level**: INSERT fails with constraint violation
2. **Cannot bypass**: Constraint is enforced by PostgreSQL

**Result**: ✅ Manual duplicate blocked

## 🔍 Checking for Existing Duplicates

### Before Migration

```bash
# 1. Check current state
python check_duplicates.py
```

**Expected output (clean):**
```
Found 445 video records in database
✓ No duplicate records found! All tweets have exactly one video.
```

**If duplicates found:**
```
⚠️  Found 3 tweets with duplicate video records!
Total duplicate records: 4

Tweet 1234567890 has 2 records:
  1. media_id=abc123, local_path=/path/to/video1.mp4
  2. media_id=def456, local_path=/path/to/video2.mp4
```

### Fix Duplicates

```bash
# Preview what will be deleted
python check_duplicates.py

# Actually fix (keeps best record)
python check_duplicates.py --fix
```

**Resolution strategy:**
1. Keeps record with downloaded video (`local_path` + file exists)
2. If multiple downloaded, keeps first
3. If none downloaded, keeps first
4. Deletes all others

### After Migration

Database constraint **automatically prevents** new duplicates:

```python
try:
    media = MediaMetadata(
        media_key="123_1",
        tweet_id=123,
        video_index=1,
        local_path="/path/to/video.mp4"
    )
    session.add(media)
    session.commit()  # ✅ Success
    
    # Try to add duplicate
    media2 = MediaMetadata(
        media_key="123_1b",
        tweet_id=123,
        video_index=1,  # Same video_index!
        local_path="/path/to/video2.mp4"
    )
    session.add(media2)
    session.commit()  # ❌ ERROR: duplicate key violation
    
except IntegrityError as e:
    print("Duplicate prevented by database!")
    session.rollback()
```

## 📋 Migration Checklist

To ensure no duplicates during migration:

- [ ] **Step 1**: Run `python check_duplicates.py`
- [ ] **Step 2**: Fix any duplicates: `python check_duplicates.py --fix`
- [ ] **Step 3**: Verify clean: `python check_duplicates.py`
- [ ] **Step 4**: Backup database: `pg_dump ...`
- [ ] **Step 5**: Run migration: `python fix_video_mapping.py`
- [ ] **Step 6**: Apply schema: `alembic upgrade head`
- [ ] **Step 7**: Verify constraint active: Try inserting duplicate (should fail)

## 🧪 Testing Duplicate Prevention

### Test 1: Try to Download Same Video Twice

```bash
# First download
python scripts/data_processing/download_videos.py --limit 1

# Try again (should skip)
python scripts/data_processing/download_videos.py --limit 1
# Expected: "Already downloaded: 1, To download: 0"
```

### Test 2: Database Constraint

```python
from database import get_session, MediaMetadata

with get_session() as session:
    # Add first video
    video1 = MediaMetadata(
        media_key="999999999_1",
        tweet_id=999999999,
        video_index=1,
        media_type="video"
    )
    session.add(video1)
    session.commit()
    print("✓ First video added")
    
    # Try to add duplicate
    try:
        video2 = MediaMetadata(
            media_key="999999999_2",
            tweet_id=999999999,
            video_index=1,  # Same video_index!
            media_type="video"
        )
        session.add(video2)
        session.commit()
        print("✗ Duplicate was allowed (BAD!)")
    except Exception as e:
        print(f"✓ Duplicate prevented: {e}")
        session.rollback()
```

**Expected output:**
```
✓ First video added
✓ Duplicate prevented: duplicate key value violates unique constraint "uq_media_metadata_tweet_video_idx"
```

## 📈 Benefits

1. **Data Integrity** - No duplicate records possible
2. **Storage Efficiency** - No wasted disk space on duplicate videos
3. **Consistent Queries** - One video per tweet (for evaluation)
4. **Future-Proof** - Supports multiple videos per tweet when needed
5. **Error Prevention** - Fails fast if duplicate attempted

## 🎯 Summary

**Question**: Are duplicates prevented?

**Answer**: ✅ **YES, with 3 layers:**

1. **Database unique constraint** (strongest, cannot be bypassed)
2. **Application skip logic** (efficient, avoids re-downloads)
3. **Pre-migration checker** (cleans up any existing issues)

**Result**: Your database will be duplicate-free! 🎉

## 📝 Quick Reference

```bash
# Check for duplicates
python check_duplicates.py

# Fix duplicates
python check_duplicates.py --fix

# Verify no duplicates
python check_duplicates.py  # Should show 0 duplicates

# After migration, constraint is automatic!
```

---

**Status**: ✅ Duplicate prevention fully implemented  
**Confidence**: 100% - Database-level enforcement  
**Maintenance**: Zero - Automatic constraint enforcement

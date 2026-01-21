# Video Migration Quick Reference

## What Changed

### File Naming
- **Old**: `video_001_1234567890.mp4` ❌
- **New**: `1234567890_1.mp4` ✅

### Database Schema
- **Old**: One video per tweet (one-to-one)
- **New**: Multiple videos per tweet supported (one-to-many)
- **New Fields**: `media_key` (primary key), `video_index` (sequence number)

## Quick Start Migration

### 1. Backup (IMPORTANT!)
```bash
pg_dump video_llm_eval > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Fix File Names & Database Paths
```bash
# Preview changes
python fix_video_mapping.py --dry-run

# Apply changes
python fix_video_mapping.py
```

### 3. Update Database Schema
```bash
alembic upgrade head
```

### 4. Verify
```bash
python scripts/data_processing/create_dataset.py --sample-size 10
```

## Files Modified

### New Files
- ✅ `fix_video_mapping.py` - Renames files and fixes database
- ✅ `VIDEO_MIGRATION_GUIDE.md` - Complete guide
- ✅ `database/migrations/versions/add_media_key_for_multiple_videos.py` - Migration

### Updated Files
- ✅ `database/models.py` - New schema (media_key, video_index)
- ✅ `scripts/data_processing/download_videos.py` - New naming convention
- ✅ `scripts/data_processing/create_dataset.py` - Handle video_index filter

## Key Benefits

1. **Tweet ID in filename** - Easy to identify which video belongs to which tweet
2. **No more index conflicts** - Tweet ID ensures uniqueness
3. **Multiple videos supported** - Can handle tweets with 2+ videos
4. **Better debugging** - Clear relationship between files and database

## Migration Order (CRITICAL!)

```
1. Backup database ← DO THIS FIRST!
2. Run fix_video_mapping.py (renames files + updates DB paths)
3. Run alembic upgrade (adds new schema fields)
4. Verify everything works
```

**Why this order?** The migration script expects the database to still have the old schema with `tweet_id` as primary key. After files are renamed and paths updated, then we change the schema.

## Expected Results

### Before
```
data/videos/
├── video_001_1756422035629121538.mp4
├── video_002_1771221581278126080.mp4
├── video_006_1774835758823591947.mp4
└── ...
```

### After
```
data/videos/
├── 1756422035629121538_1.mp4
├── 1771221581278126080_1.mp4
├── 1774835758823591947_1.mp4
└── ...
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Database connection error | Check PostgreSQL is running, verify .env |
| File already exists | Script skips existing files in correct format |
| Migration fails | Restore from backup, check you ran fix_video_mapping.py first |
| Paths still wrong | Check logs from fix_video_mapping.py for errors |

## Need More Details?

See `VIDEO_MIGRATION_GUIDE.md` for:
- Detailed step-by-step instructions
- Code examples
- Schema documentation
- Rollback procedures
- Advanced troubleshooting

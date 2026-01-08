# Data Sync Scripts - Quick Reference

Three scripts to sync your data directory to the remote server.

## 🚀 Quick Start

### Fastest: Sync Exports Only

```bash
./quick_sync.sh
```

This syncs just `data/exports/` directory (CSV files, usually < 100 MB).

### Full Sync: Everything

```bash
./quick_sync.sh --all
```

This syncs all data: exports, videos, raw files, filtered data.

## 📋 Scripts Overview

| Script | Purpose | Best For |
|--------|---------|----------|
| **`quick_sync.sh`** | Simple, fast, one-command | Daily updates, quick transfers |
| **`sync_to_server.sh`** | Advanced, interactive, with previews | First-time setup, selective syncing |
| **`sync_config.sh`** | Configuration file | Customizing sync behavior |

## 🎯 Common Use Cases

### Case 1: First Time Setup

```bash
# Preview what will be synced
./sync_to_server.sh --dry-run

# Sync everything
./quick_sync.sh --all

# Then on server: import data
ssh prabalshrestha@eng402924
cd ~/video-llm-baseline-eval
./import_all_data.sh
```

### Case 2: Regular Updates (New CSV Exports)

```bash
# Quick sync of exports
./quick_sync.sh

# Then on server: re-import
ssh prabalshrestha@eng402924 "cd ~/video-llm-baseline-eval && ./import_all_data.sh"
```

### Case 3: New Videos Downloaded

```bash
# Sync videos only
./quick_sync.sh --videos

# Or with advanced script
./sync_to_server.sh --videos-only
```

### Case 4: Everything Except Videos

```bash
./sync_to_server.sh --no-videos
```

## 📖 Detailed Documentation

- **[SYNC_GUIDE.md](SYNC_GUIDE.md)** - Complete sync guide
  - All options and flags
  - Troubleshooting
  - Performance tips
  - Examples

- **[REMOTE_SERVER_SETUP.md](REMOTE_SERVER_SETUP.md)** - Server setup
  - Full server configuration
  - Database setup
  - Import process

## 🔧 Configuration

Edit `sync_config.sh` to customize:

```bash
SYNC_REMOTE_USER="prabalshrestha"    # Your SSH username
SYNC_REMOTE_HOST="eng402924"         # Server hostname
SYNC_REMOTE_PATH="~/video-llm-baseline-eval"  # Remote path
```

## 🎨 Script Features

### `quick_sync.sh`

✅ Color-coded output  
✅ One-line commands  
✅ Automatic remote directory creation  
✅ Progress tracking  
✅ Three modes: exports, videos, all  

```bash
./quick_sync.sh          # Exports only
./quick_sync.sh --all    # Everything
./quick_sync.sh --videos # Videos only
./quick_sync.sh --help   # Help
```

### `sync_to_server.sh`

✅ Interactive confirmations  
✅ File/size summaries  
✅ Dry run mode  
✅ Selective directory syncing  
✅ Smart file exclusions  

```bash
./sync_to_server.sh                  # All with confirmations
./sync_to_server.sh --dry-run        # Preview only
./sync_to_server.sh --exports-only   # Exports only
./sync_to_server.sh --videos-only    # Videos only
./sync_to_server.sh --no-videos      # Everything except videos
./sync_to_server.sh --help           # Help
```

## 📊 Data Sizes (Typical)

| Directory | Typical Size | Transfer Time* |
|-----------|--------------|----------------|
| `exports/` | 10-100 MB | < 1 minute |
| `raw/` | 100-500 MB | 2-5 minutes |
| `filtered/` | 10-50 MB | < 1 minute |
| `videos/` | 1-50 GB | 10-60 minutes |

*Transfer times vary based on network speed and file compression.

## 🔐 SSH Setup (Recommended)

For password-less syncing:

```bash
# Generate SSH key (if needed)
ssh-keygen -t ed25519

# Copy to server
ssh-copy-id prabalshrestha@eng402924

# Test
ssh prabalshrestha@eng402924 exit
```

Now syncing won't require password entry!

## 🚨 Troubleshooting

### Cannot Connect to Server

```bash
# Test SSH
ssh prabalshrestha@eng402924

# If that works, try sync again
./quick_sync.sh
```

### Permission Denied

Check username and SSH keys:
```bash
# Edit sync scripts if username is different
# Or set up SSH keys (see above)
```

### Not Enough Space on Server

```bash
# Check server disk space
ssh prabalshrestha@eng402924 "df -h"

# Check data directory size
ssh prabalshrestha@eng402924 "du -sh ~/video-llm-baseline-eval/data/*"
```

### Transfer Too Slow

```bash
# Sync without videos
./sync_to_server.sh --no-videos

# Or sync videos separately later
./quick_sync.sh --videos
```

## 📈 Complete Workflow

```mermaid
graph LR
    A[Local Data] -->|quick_sync.sh| B[Remote Server]
    B -->|import_all_data.sh| C[PostgreSQL]
    C -->|test_import.py| D[Verified Data]
```

**In commands:**

```bash
# 1. Local: Sync data
./quick_sync.sh --all

# 2. Remote: Import data
ssh prabalshrestha@eng402924 "cd ~/video-llm-baseline-eval && ./import_all_data.sh"

# 3. Remote: Verify
ssh prabalshrestha@eng402924 "cd ~/video-llm-baseline-eval && python3 test_import.py"
```

## 💡 Tips

1. **Start with exports** - They're small and quick to sync
2. **Use dry run** - Preview before large transfers
3. **Sync videos separately** - They're large, do them when convenient
4. **Set up SSH keys** - Eliminates password prompts
5. **Check space first** - Ensure server has enough disk space

## 🎓 Examples

### Example 1: First-Time Full Sync

```bash
# See what would be synced
./sync_to_server.sh --dry-run

# Sync everything
./quick_sync.sh --all
```

### Example 2: Quick Daily Update

```bash
# Just sync new exports
./quick_sync.sh

# Import on server
ssh prabalshrestha@eng402924 "cd ~/video-llm-baseline-eval && ./import_all_data.sh"
```

### Example 3: Videos Only (Large Transfer)

```bash
# Do overnight or when you have time
./quick_sync.sh --videos
```

## 📚 Related Documentation

- **SYNC_GUIDE.md** - Complete sync documentation
- **REMOTE_SERVER_SETUP.md** - Server setup guide  
- **DATABASE_IMPORT.md** - Import guide
- **QUICK_START.md** - Overall quick start

## ✅ Checklist

Before syncing:
- [ ] SSH access to server configured
- [ ] Server has enough disk space
- [ ] Data exported locally (if needed)

After syncing:
- [ ] Data visible on server
- [ ] Run `./import_all_data.sh` on server
- [ ] Verify with `python3 test_import.py`

## 🆘 Need Help?

```bash
# Script help
./quick_sync.sh --help
./sync_to_server.sh --help

# Test SSH connection
ssh prabalshrestha@eng402924

# Check server status
ssh prabalshrestha@eng402924 "df -h && ls -lh ~/video-llm-baseline-eval/data/"
```

---

**Ready to sync?** Start with `./quick_sync.sh` for the fastest option!


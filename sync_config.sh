#!/bin/bash
#
# Sync configuration
# Edit these values to match your setup
#

# Remote server details
export SYNC_REMOTE_USER="prabalshrestha"
export SYNC_REMOTE_HOST="eng402924"
export SYNC_REMOTE_PATH="~/video-llm-baseline-eval"

# What to sync (true/false)
export SYNC_EXPORTS=true
export SYNC_VIDEOS=true
export SYNC_RAW=true
export SYNC_FILTERED=true

# Rsync options
export SYNC_COMPRESS=true          # Use compression
export SYNC_PROGRESS=true          # Show progress
export SYNC_VERBOSE=true           # Verbose output
export SYNC_DELETE=false           # Delete files on remote that don't exist locally (DANGEROUS!)

# Optional: Bandwidth limit (in KB/s, set to 0 for unlimited)
export SYNC_BANDWIDTH_LIMIT=0

# Optional: Exclude patterns (space-separated)
export SYNC_EXCLUDE="*.pyc __pycache__ .DS_Store *.tmp"


#!/bin/bash
#
# Quick sync - simple one-liner to sync data to server
#
# Usage:
#   ./quick_sync.sh              # Sync exports only (fast)
#   ./quick_sync.sh --all        # Sync everything
#   ./quick_sync.sh --videos     # Sync videos only
#

set -e

# Configuration
REMOTE_USER="prabalshrestha"
REMOTE_HOST="eng402924"
REMOTE_PATH="~/video-llm-baseline-eval"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Quick Sync to Server${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Parse arguments
MODE="exports"
if [ "$1" = "--all" ]; then
    MODE="all"
elif [ "$1" = "--videos" ]; then
    MODE="videos"
elif [ "$1" = "--help" ]; then
    echo "Usage: $0 [MODE]"
    echo ""
    echo "Modes:"
    echo "  (no args)    Sync exports only (default, fast)"
    echo "  --all        Sync everything (exports, videos, raw, filtered)"
    echo "  --videos     Sync videos only"
    echo "  --help       Show this help"
    echo ""
    echo "Examples:"
    echo "  $0              # Quick sync of exports"
    echo "  $0 --all        # Full sync"
    echo "  $0 --videos     # Videos only"
    exit 0
fi

echo -e "${YELLOW}Mode: $MODE${NC}"
echo -e "Remote: ${REMOTE_USER}@${REMOTE_HOST}"
echo ""

# Check SSH connection
echo -e "${BLUE}Checking connection...${NC}"
echo "Note: You'll be prompted for your password if SSH keys aren't set up."
echo ""
if ! ssh -o ConnectTimeout=10 ${REMOTE_USER}@${REMOTE_HOST} exit 2>/dev/null; then
    echo -e "${YELLOW}SSH key authentication not available.${NC}"
    echo -e "${YELLOW}You'll be prompted for your password during sync.${NC}"
    echo ""
fi

# Ensure remote directory exists
echo -e "${BLUE}Preparing remote directories...${NC}"
ssh ${REMOTE_USER}@${REMOTE_HOST} "mkdir -p ${REMOTE_PATH}/data/{exports,videos,raw,filtered}"

# Sync based on mode
case $MODE in
    "exports")
        echo ""
        echo -e "${BLUE}Syncing exports...${NC}"
        rsync -avz --progress \
            --exclude='*.pyc' --exclude='__pycache__' --exclude='.DS_Store' \
            data/exports/ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/data/exports/
        echo -e "${GREEN}✓ Exports synced${NC}"
        ;;
    
    "videos")
        echo ""
        echo -e "${BLUE}Syncing videos (may take a while)...${NC}"
        rsync -avz --progress \
            --exclude='*.pyc' --exclude='__pycache__' --exclude='.DS_Store' \
            data/videos/ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/data/videos/
        echo -e "${GREEN}✓ Videos synced${NC}"
        ;;
    
    "all")
        echo ""
        echo -e "${BLUE}Syncing all data directories...${NC}"
        echo ""
        
        for dir in exports raw filtered videos; do
            if [ -d "data/$dir" ]; then
                echo -e "${BLUE}Syncing $dir...${NC}"
                rsync -avz --progress \
                    --exclude='*.pyc' --exclude='__pycache__' --exclude='.DS_Store' \
                    data/$dir/ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/data/$dir/
                echo -e "${GREEN}✓ $dir synced${NC}"
                echo ""
            fi
        done
        ;;
esac

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Sync Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Next steps on server:"
echo "  1. ssh ${REMOTE_USER}@${REMOTE_HOST}"
echo "  2. cd ${REMOTE_PATH}"
echo "  3. ./import_all_data.sh"
echo ""


#!/bin/bash
#
# Sync data directory to remote server
#
# Usage:
#   ./sync_to_server.sh                    # Sync everything
#   ./sync_to_server.sh --exports-only     # Only sync exports
#   ./sync_to_server.sh --videos-only      # Only sync videos
#   ./sync_to_server.sh --dry-run          # Show what would be synced
#

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

# Remote server configuration
REMOTE_USER="prabalshrestha"
REMOTE_HOST="eng402924"
REMOTE_PATH="~/video-llm-baseline-eval"

# Local paths
LOCAL_DATA_DIR="data"

# Rsync options
RSYNC_OPTS="-avz --progress"

# ============================================================================
# PARSE ARGUMENTS
# ============================================================================

SYNC_MODE="all"
DRY_RUN=""
EXCLUDE_VIDEOS=""
EXCLUDE_EXPORTS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --exports-only)
            SYNC_MODE="exports"
            shift
            ;;
        --videos-only)
            SYNC_MODE="videos"
            shift
            ;;
        --no-videos)
            EXCLUDE_VIDEOS="--exclude=videos/"
            shift
            ;;
        --no-exports)
            EXCLUDE_EXPORTS="--exclude=exports/"
            shift
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            echo "DRY RUN MODE - No files will actually be transferred"
            echo ""
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --exports-only    Only sync data/exports directory"
            echo "  --videos-only     Only sync data/videos directory"
            echo "  --no-videos       Exclude videos from sync"
            echo "  --no-exports      Exclude exports from sync"
            echo "  --dry-run         Show what would be synced without actually syncing"
            echo "  --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                      # Sync everything"
            echo "  $0 --exports-only       # Only sync exports"
            echo "  $0 --no-videos          # Sync everything except videos"
            echo "  $0 --dry-run            # Preview what would be synced"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

print_section() {
    echo ""
    echo "------------------------------------------------------------"
    echo "$1"
    echo "------------------------------------------------------------"
}

check_ssh_connection() {
    echo "Checking SSH connection to ${REMOTE_USER}@${REMOTE_HOST}..."
    echo "Note: You may be prompted for your password if SSH keys are not set up."
    echo ""
    
    # Try to connect (will prompt for password if needed)
    if ssh -o ConnectTimeout=10 ${REMOTE_USER}@${REMOTE_HOST} exit; then
        echo ""
        echo "✓ SSH connection successful"
        return 0
    else
        echo ""
        echo "✗ Cannot connect to server"
        echo ""
        echo "Please ensure:"
        echo "  1. Server is reachable: ping ${REMOTE_HOST}"
        echo "  2. You have SSH access with correct username"
        echo "  3. You know the password (or set up SSH keys for easier access)"
        return 1
    fi
}

get_dir_size() {
    local dir=$1
    if [ -d "$dir" ]; then
        du -sh "$dir" 2>/dev/null | cut -f1
    else
        echo "N/A"
    fi
}

count_files() {
    local dir=$1
    if [ -d "$dir" ]; then
        find "$dir" -type f 2>/dev/null | wc -l | tr -d ' '
    else
        echo "0"
    fi
}

sync_directory() {
    local src=$1
    local dest=$2
    local description=$3
    
    print_section "$description"
    
    if [ ! -d "$src" ]; then
        echo "⚠ Source directory not found: $src"
        echo "Skipping..."
        return
    fi
    
    local size=$(get_dir_size "$src")
    local files=$(count_files "$src")
    
    echo "Source: $src"
    echo "Size: $size"
    echo "Files: $files"
    echo ""
    
    if [ -z "$DRY_RUN" ]; then
        read -p "Proceed with sync? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipped."
            return
        fi
    fi
    
    echo "Syncing..."
    rsync $RSYNC_OPTS $DRY_RUN \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='.DS_Store' \
        "$src/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/$dest/"
    
    if [ $? -eq 0 ]; then
        echo "✓ Sync complete"
    else
        echo "✗ Sync failed"
        exit 1
    fi
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

print_header "Sync Data to Remote Server"

echo "Remote: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"
echo "Mode: $SYNC_MODE"
if [ -n "$DRY_RUN" ]; then
    echo "Dry Run: Yes (no files will be transferred)"
fi
echo ""

# Check SSH connection
if ! check_ssh_connection; then
    exit 1
fi

# Ensure remote directory exists
print_section "Preparing remote directory"
echo "Creating remote data directory if needed..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "mkdir -p ${REMOTE_PATH}/data/exports ${REMOTE_PATH}/data/videos ${REMOTE_PATH}/data/raw ${REMOTE_PATH}/data/filtered"
echo "✓ Remote directories ready"

# Sync based on mode
case $SYNC_MODE in
    "exports")
        sync_directory "data/exports" "data/exports" "Syncing Exports Directory"
        ;;
    
    "videos")
        sync_directory "data/videos" "data/videos" "Syncing Videos Directory"
        ;;
    
    "all")
        # Show summary first
        print_section "Sync Summary"
        echo "The following directories will be synced:"
        echo ""
        echo "  data/exports/     $(get_dir_size data/exports)    $(count_files data/exports) files"
        echo "  data/videos/      $(get_dir_size data/videos)     $(count_files data/videos) files"
        echo "  data/raw/         $(get_dir_size data/raw)        $(count_files data/raw) files"
        echo "  data/filtered/    $(get_dir_size data/filtered)   $(count_files data/filtered) files"
        echo ""
        
        if [ -z "$DRY_RUN" ]; then
            read -p "Proceed with full sync? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Sync cancelled."
                exit 0
            fi
        fi
        
        # Sync each directory
        print_section "Syncing All Data Directories"
        
        # Exports (usually small)
        if [ -z "$EXCLUDE_EXPORTS" ] && [ -d "data/exports" ]; then
            echo "1/4: Syncing exports..."
            rsync $RSYNC_OPTS $DRY_RUN \
                --exclude='*.pyc' \
                --exclude='__pycache__' \
                "data/exports/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/data/exports/"
            echo "✓ Exports synced"
        fi
        
        # Raw data (usually large)
        if [ -d "data/raw" ]; then
            echo ""
            echo "2/4: Syncing raw data..."
            rsync $RSYNC_OPTS $DRY_RUN \
                --exclude='*.pyc' \
                --exclude='__pycache__' \
                "data/raw/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/data/raw/"
            echo "✓ Raw data synced"
        fi
        
        # Filtered data
        if [ -d "data/filtered" ]; then
            echo ""
            echo "3/4: Syncing filtered data..."
            rsync $RSYNC_OPTS $DRY_RUN \
                --exclude='*.pyc' \
                --exclude='__pycache__' \
                "data/filtered/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/data/filtered/"
            echo "✓ Filtered data synced"
        fi
        
        # Videos (usually very large)
        if [ -z "$EXCLUDE_VIDEOS" ] && [ -d "data/videos" ]; then
            echo ""
            echo "4/4: Syncing videos (this may take a while)..."
            rsync $RSYNC_OPTS $DRY_RUN \
                --exclude='*.pyc' \
                --exclude='__pycache__' \
                "data/videos/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/data/videos/"
            echo "✓ Videos synced"
        fi
        ;;
esac

# Done
print_header "Sync Complete"

if [ -z "$DRY_RUN" ]; then
    echo "✓ All data synced to ${REMOTE_USER}@${REMOTE_HOST}"
    echo ""
    echo "Next steps on the remote server:"
    echo "  1. SSH to server: ssh ${REMOTE_USER}@${REMOTE_HOST}"
    echo "  2. Navigate to project: cd ${REMOTE_PATH}"
    echo "  3. Import data: ./import_all_data.sh"
    echo "  4. Verify: python3 test_import.py"
else
    echo "This was a dry run. No files were actually transferred."
    echo "Remove --dry-run to perform the actual sync."
fi

echo ""


#!/bin/bash
#
# Quick import script - imports all data from exports directory
# 
# Usage:
#   ./import_all_data.sh
#
# Or with custom exports directory:
#   ./import_all_data.sh /path/to/exports

set -e

# Activate virtual environment if it exists
# if [ -d "venv" ]; then
#     echo "Activating virtual environment..."
#     source venv/bin/activate
# fi

# Set exports directory
EXPORTS_DIR="${1:-data/exports}"

echo "=================================================="
echo "Importing all data from: $EXPORTS_DIR"
echo "=================================================="

# Run the import script
python3 import_from_exports.py --exports-dir "$EXPORTS_DIR"

echo ""
echo "=================================================="
echo "Import complete!"
echo "=================================================="
echo ""
echo "To verify the data, run:"
echo "  python3 setup_database.py --verify"


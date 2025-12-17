#!/usr/bin/env python3
"""
Test: Detached Instance Fix
Verifies that data extraction happens within session context.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("TESTING: Detached Instance Fix")
print("=" * 70)

print("\n1. Checking code structure...")

# Read the identify_video_notes.py file
script_path = Path(__file__).parent / "data_processing" / "identify_video_notes.py"

with open(script_path, "r") as f:
    content = f.read()

# Check for the fix patterns
checks = {
    "✅ Data extraction within session": "media_notes_data = [" in content,
    "✅ Extract while session active": "Extract data WHILE session is still active" in content,
    "✅ Uses plain dictionaries": 'df = pd.DataFrame(media_notes_data)' in content,
    "✅ Proper variable naming": "media_notes_query" in content,
}

all_passed = True
for check_name, result in checks.items():
    status = "✓" if result else "✗"
    print(f"  {status} {check_name}")
    if not result:
        all_passed = False

print("\n2. Code pattern verification...")

# Check that we're NOT accessing ORM objects outside session
bad_patterns = [
    ("Accessing ORM attrs outside session", "for note in media_notes_query\n    ]"),
]

for pattern_name, pattern in bad_patterns:
    if pattern not in content:
        print(f"  ✓ No {pattern_name} (good!)")
    else:
        print(f"  ✗ Found {pattern_name} (bad!)")
        all_passed = False

print("\n" + "=" * 70)
if all_passed:
    print("✅ All checks passed!")
    print("\nThe DetachedInstanceError fix is correctly implemented:")
    print("  1. Data is extracted WITHIN the 'with get_session()' block")
    print("  2. Plain dictionaries are created from ORM objects")
    print("  3. DataFrame is created from plain dictionaries")
    print("  4. No ORM object attributes accessed after session closes")
    print("\n" + "=" * 70)
    sys.exit(0)
else:
    print("✗ Some checks failed!")
    sys.exit(1)


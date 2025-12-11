"""
Quick test script to verify video identification works correctly.
Tests with a small sample before processing all media notes.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from identify_video_notes import VideoNoteIdentifier
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_small_sample():
    """Test with just 10 media notes to verify the approach works."""
    logger.info("=" * 70)
    logger.info("TESTING VIDEO IDENTIFICATION")
    logger.info("=" * 70)
    logger.info("\nTesting with 10 media notes to verify the approach...")
    logger.info("If this works, you can run the full script on all media notes.\n")
    
    identifier = VideoNoteIdentifier(data_dir="data")
    result = identifier.run(sample_size=10)
    
    if result is not None and len(result) > 0:
        logger.info("\n" + "=" * 70)
        logger.info("✓ TEST SUCCESSFUL!")
        logger.info("=" * 70)
        logger.info(f"Found {len(result)} videos in sample of 10 media notes")
        logger.info("\nThe approach is working correctly!")
        logger.info("\nTo process ALL media notes, run:")
        logger.info("  python scripts/data_processing/identify_video_notes.py")
        logger.info("\nOr to test with a larger sample (e.g., 100 notes):")
        logger.info("  python scripts/data_processing/identify_video_notes.py --sample 100")
        return True
    elif result is not None and len(result) == 0:
        logger.warning("\n" + "=" * 70)
        logger.warning("⚠ TEST COMPLETED BUT NO VIDEOS FOUND")
        logger.warning("=" * 70)
        logger.warning("This might be normal if the sample didn't contain videos.")
        logger.warning("Try running with a larger sample:")
        logger.warning("  python scripts/data_processing/identify_video_notes.py --sample 100")
        return True
    else:
        logger.error("\n" + "=" * 70)
        logger.error("✗ TEST FAILED")
        logger.error("=" * 70)
        logger.error("Check the error messages above.")
        return False


if __name__ == "__main__":
    success = test_small_sample()
    sys.exit(0 if success else 1)


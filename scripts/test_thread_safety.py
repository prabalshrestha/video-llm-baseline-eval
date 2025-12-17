#!/usr/bin/env python3
"""
Test Thread-Safety of Database Operations
Verifies that multiple threads can safely access the database.
"""

import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_session, MediaMetadata

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_thread_safe_query(thread_id: int) -> dict:
    """
    Test that each thread can safely create its own session and query.
    
    Args:
        thread_id: Identifier for this thread
    
    Returns:
        Dict with thread_id and query results
    """
    try:
        # Each thread creates its OWN session - this is thread-safe
        with get_session() as session:
            # Query some data
            count = session.query(MediaMetadata).count()
            
            # Get a sample record if exists
            sample = session.query(MediaMetadata).first()
            
            return {
                "thread_id": thread_id,
                "success": True,
                "count": count,
                "has_sample": sample is not None,
                "error": None
            }
    except Exception as e:
        return {
            "thread_id": thread_id,
            "success": False,
            "count": 0,
            "has_sample": False,
            "error": str(e)
        }


def main():
    """Test multi-threaded database access."""
    logger.info("=" * 70)
    logger.info("THREAD-SAFETY TEST")
    logger.info("=" * 70)
    
    num_threads = 10
    logger.info(f"\nTesting with {num_threads} concurrent threads...")
    logger.info("Each thread will create its own session and query the database.\n")
    
    results = []
    
    # Run queries in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit all tasks
        futures = {
            executor.submit(test_thread_safe_query, i): i 
            for i in range(num_threads)
        }
        
        # Collect results
        for future in as_completed(futures):
            thread_id = futures[future]
            try:
                result = future.result()
                results.append(result)
                
                if result["success"]:
                    logger.info(
                        f"✓ Thread {result['thread_id']:2d}: "
                        f"Success (count={result['count']})"
                    )
                else:
                    logger.error(
                        f"✗ Thread {result['thread_id']:2d}: "
                        f"Failed - {result['error']}"
                    )
            except Exception as e:
                logger.error(f"✗ Thread {thread_id:2d}: Exception - {e}")
                results.append({
                    "thread_id": thread_id,
                    "success": False,
                    "error": str(e)
                })
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("RESULTS")
    logger.info("=" * 70)
    
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    
    logger.info(f"Total threads: {len(results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    
    if failed == 0:
        logger.info("\n✅ All threads completed successfully!")
        logger.info("✅ Thread-safe database access is working correctly.")
        return 0
    else:
        logger.error(f"\n❌ {failed} thread(s) failed!")
        logger.error("❌ There may be thread-safety issues.")
        
        # Show errors
        for result in results:
            if not result["success"]:
                logger.error(f"  Thread {result['thread_id']}: {result['error']}")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())


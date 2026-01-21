#!/usr/bin/env python3
"""Quick check of database paths"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import get_session
from sqlalchemy import text

with get_session() as session:
    # Check how many have local_path set
    sql = text("""
        SELECT 
            COUNT(*) as total,
            COUNT(local_path) as with_path,
            COUNT(*) - COUNT(local_path) as without_path
        FROM media_metadata
        WHERE media_type = 'video'
    """)
    
    result = session.execute(sql).fetchone()
    print(f"Total video records: {result[0]}")
    print(f"With local_path: {result[1]}")
    print(f"Without local_path (NULL): {result[2]}")
    print()
    
    # Show sample paths
    sql2 = text("""
        SELECT tweet_id, local_path
        FROM media_metadata
        WHERE media_type = 'video'
        AND local_path IS NOT NULL
        LIMIT 10
    """)
    
    print("Sample database paths:")
    result2 = session.execute(sql2)
    for row in result2:
        print(f"  Tweet {row[0]}: {row[1]}")

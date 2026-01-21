#!/usr/bin/env python
"""
Quick test script to verify import worked correctly.

This script performs sanity checks on imported data.
"""

import sys
from pathlib import Path
from database.config import SessionLocal, check_connection
from database.models import Tweet, Note, MediaMetadata
from sqlalchemy import func, text

def test_database():
    """Run database tests."""
    
    print("=" * 60)
    print("Database Import Verification")
    print("=" * 60)
    
    # Check connection
    print("\n1. Checking database connection...")
    if not check_connection():
        print("   ✗ Database connection failed!")
        return False
    print("   ✓ Database connection successful")
    
    session = SessionLocal()
    
    try:
        # Count records
        print("\n2. Counting records...")
        tweet_count = session.query(func.count(Tweet.tweet_id)).scalar()
        note_count = session.query(func.count(Note.note_id)).scalar()
        media_count = session.query(func.count(MediaMetadata.tweet_id)).scalar()
        
        print(f"   Tweets: {tweet_count:,}")
        print(f"   Notes: {note_count:,}")
        print(f"   Media: {media_count:,}")
        
        if tweet_count == 0:
            print("   ⚠ Warning: No tweets found!")
        if note_count == 0:
            print("   ⚠ Warning: No notes found!")
        if media_count == 0:
            print("   ⚠ Warning: No media metadata found!")
        
        # Check foreign key relationships
        print("\n3. Checking foreign key relationships...")
        
        # Notes should reference existing tweets
        orphaned_notes = session.query(Note).filter(
            ~Note.tweet_id.in_(
                session.query(Tweet.tweet_id)
            )
        ).count()
        
        if orphaned_notes > 0:
            print(f"   ✗ Found {orphaned_notes} notes with missing tweets!")
        else:
            print(f"   ✓ All notes have valid tweet references")
        
        # Media should reference existing tweets
        orphaned_media = session.query(MediaMetadata).filter(
            ~MediaMetadata.tweet_id.in_(
                session.query(Tweet.tweet_id)
            )
        ).count()
        
        if orphaned_media > 0:
            print(f"   ✗ Found {orphaned_media} media records with missing tweets!")
        else:
            print(f"   ✓ All media records have valid tweet references")
        
        # Check data quality
        print("\n4. Checking data quality...")
        
        # Tweets with text
        tweets_with_text = session.query(Tweet).filter(
            Tweet.text.isnot(None),
            Tweet.text != ''
        ).count()
        print(f"   Tweets with text: {tweets_with_text:,} ({100*tweets_with_text/max(tweet_count,1):.1f}%)")
        
        # Tweets with engagement data
        tweets_with_likes = session.query(Tweet).filter(
            Tweet.likes.isnot(None)
        ).count()
        print(f"   Tweets with likes data: {tweets_with_likes:,} ({100*tweets_with_likes/max(tweet_count,1):.1f}%)")
        
        # Notes with classification
        notes_classified = session.query(Note).filter(
            Note.classification.isnot(None)
        ).count()
        print(f"   Notes with classification: {notes_classified:,} ({100*notes_classified/max(note_count,1):.1f}%)")
        
        # Media notes
        media_notes = session.query(Note).filter(
            Note.is_media_note == True
        ).count()
        print(f"   Media notes: {media_notes:,} ({100*media_notes/max(note_count,1):.1f}%)")
        
        # Check sample data
        print("\n5. Sample data...")
        
        sample_tweet = session.query(Tweet).first()
        if sample_tweet:
            print(f"   Sample tweet ID: {sample_tweet.tweet_id}")
            print(f"   Author: @{sample_tweet.author_username or 'unknown'}")
            print(f"   Likes: {sample_tweet.likes or 0}")
            print(f"   Has media: {sample_tweet.media_metadata is not None}")
            print(f"   Note count: {len(sample_tweet.notes)}")
        
        # Engagement stats
        print("\n6. Engagement statistics...")
        
        avg_likes = session.query(func.avg(Tweet.likes)).filter(
            Tweet.likes.isnot(None)
        ).scalar()
        max_likes = session.query(func.max(Tweet.likes)).filter(
            Tweet.likes.isnot(None)
        ).scalar()
        
        print(f"   Average likes: {avg_likes:.0f}")
        print(f"   Max likes: {max_likes:,}")
        
        # Classification breakdown
        print("\n7. Note classifications...")
        
        classifications = session.query(
            Note.classification,
            func.count(Note.note_id)
        ).group_by(Note.classification).all()
        
        for classification, count in classifications:
            if classification:
                print(f"   {classification}: {count:,}")
        
        print("\n" + "=" * 60)
        print("✓ Verification complete!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)


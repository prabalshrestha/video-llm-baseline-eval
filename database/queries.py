"""
Helper query functions for common database operations.

Provides both SQLAlchemy ORM and raw SQL query examples.
"""

import logging
from typing import List, Dict, Optional, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.models import Note, Tweet, MediaMetadata

logger = logging.getLogger(__name__)


def get_notes_by_tweet_id(session: Session, tweet_id: int) -> List[Note]:
    """
    Get all notes for a specific tweet.
    
    Args:
        session: Database session
        tweet_id: Tweet ID to query
        
    Returns:
        List of Note objects
    """
    return session.query(Note).filter(Note.tweet_id == tweet_id).all()


def get_media_metadata_by_tweet_id(session: Session, tweet_id: int) -> Optional[MediaMetadata]:
    """
    Get media metadata for a specific tweet.
    
    Args:
        session: Database session
        tweet_id: Tweet ID to query
        
    Returns:
        MediaMetadata object or None
    """
    return session.query(MediaMetadata).filter(MediaMetadata.tweet_id == tweet_id).first()


def get_misleading_media(
    session: Session,
    min_engagement: int = 1000,
    media_type: Optional[str] = None,
    classification: str = "MISINFORMED_OR_POTENTIALLY_MISLEADING"
) -> List[tuple]:
    """
    Find misleading media content with high engagement.
    
    Args:
        session: Database session
        min_engagement: Minimum number of likes
        media_type: Filter by media type ('video' or 'image'), None for all
        classification: Classification type to filter
        
    Returns:
        List of (Tweet, Note, MediaMetadata) tuples
    """
    query = (
        session.query(Tweet, Note, MediaMetadata)
        .join(Note, Tweet.tweet_id == Note.tweet_id)
        .outerjoin(MediaMetadata, Tweet.tweet_id == MediaMetadata.tweet_id)
        .filter(
            Note.classification == classification,
            Tweet.likes >= min_engagement
        )
    )
    
    if media_type:
        query = query.filter(MediaMetadata.media_type == media_type)
    
    return query.all()


def get_media_by_note_id(session: Session, note_id: int) -> Optional[Dict[str, Any]]:
    """
    Get full record (note, tweet, media metadata) by note ID.
    
    Args:
        session: Database session
        note_id: Note ID to query
        
    Returns:
        Dictionary with note, tweet, and media_metadata keys
    """
    result = (
        session.query(Note, Tweet, MediaMetadata)
        .join(Tweet, Note.tweet_id == Tweet.tweet_id)
        .outerjoin(MediaMetadata, Tweet.tweet_id == MediaMetadata.tweet_id)
        .filter(Note.note_id == note_id)
        .first()
    )
    
    if result:
        note, tweet, media = result
        return {
            "note": note,
            "tweet": tweet,
            "media_metadata": media
        }
    return None


def get_evaluation_dataset(
    session: Session,
    limit: Optional[int] = None,
    classification: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get complete evaluation dataset with all joined data.
    
    Args:
        session: Database session
        limit: Optional limit on number of results
        classification: Optional filter by classification
        
    Returns:
        List of dictionaries with complete data
    """
    query = (
        session.query(Note, Tweet, MediaMetadata)
        .join(Tweet, Note.tweet_id == Tweet.tweet_id)
        .outerjoin(MediaMetadata, Tweet.tweet_id == MediaMetadata.tweet_id)
    )
    
    if classification:
        query = query.filter(Note.classification == classification)
    
    if limit:
        query = query.limit(limit)
    
    results = []
    for note, tweet, media in query.all():
        results.append({
            "note_id": note.note_id,
            "tweet_id": tweet.tweet_id,
            "classification": note.classification,
            "summary": note.summary,
            "is_media_note": note.is_media_note,
            "tweet_text": tweet.text,
            "author_username": tweet.author_username,
            "likes": tweet.likes,
            "retweets": tweet.retweets,
            "media_type": media.media_type if media else None,
            "media_title": media.title if media else None,
            "duration_ms": media.duration_ms if media else None,
            "local_path": media.local_path if media else None,
        })
    
    return results


def get_engagement_stats(session: Session) -> Dict[str, Any]:
    """
    Get aggregate engagement statistics.
    
    Args:
        session: Database session
        
    Returns:
        Dictionary with engagement statistics
    """
    result = session.execute(
        text("""
            SELECT 
                COUNT(DISTINCT t.tweet_id) as total_tweets,
                COUNT(DISTINCT n.note_id) as total_notes,
                COUNT(DISTINCT mm.tweet_id) as total_media,
                AVG(t.likes) as avg_likes,
                MAX(t.likes) as max_likes,
                SUM(t.likes) as total_likes,
                COUNT(DISTINCT CASE WHEN n.classification = 'MISINFORMED_OR_POTENTIALLY_MISLEADING' THEN n.note_id END) as misleading_count,
                COUNT(DISTINCT CASE WHEN n.classification = 'NOT_MISLEADING' THEN n.note_id END) as not_misleading_count
            FROM tweets t
            LEFT JOIN notes n ON t.tweet_id = n.tweet_id
            LEFT JOIN media_metadata mm ON t.tweet_id = mm.tweet_id
        """)
    ).fetchone()
    
    return {
        "total_tweets": result[0] if result else 0,
        "total_notes": result[1] if result else 0,
        "total_media": result[2] if result else 0,
        "avg_likes": float(result[3]) if result and result[3] else 0.0,
        "max_likes": result[4] if result else 0,
        "total_likes": result[5] if result else 0,
        "misleading_count": result[6] if result else 0,
        "not_misleading_count": result[7] if result else 0,
    }


def filter_by_classification_and_media(
    session: Session,
    classification: str,
    media_type: Optional[str] = None,
    has_media: bool = True
) -> List[tuple]:
    """
    Filter notes by classification and media type.
    
    Args:
        session: Database session
        classification: Classification to filter by
        media_type: Optional media type filter ('video' or 'image')
        has_media: If True, only return notes with media metadata
        
    Returns:
        List of (Note, Tweet, MediaMetadata) tuples
    """
    query = (
        session.query(Note, Tweet, MediaMetadata)
        .join(Tweet, Note.tweet_id == Tweet.tweet_id)
    )
    
    if has_media:
        query = query.join(MediaMetadata, Tweet.tweet_id == MediaMetadata.tweet_id)
    else:
        query = query.outerjoin(MediaMetadata, Tweet.tweet_id == MediaMetadata.tweet_id)
    
    query = query.filter(Note.classification == classification)
    
    if media_type:
        query = query.filter(MediaMetadata.media_type == media_type)
    
    return query.all()


def export_to_json_format(session: Session, output_limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Export data in a format similar to the existing dataset.json.
    
    Args:
        session: Database session
        output_limit: Optional limit on results
        
    Returns:
        List of dictionaries formatted like dataset.json
    """
    query = (
        session.query(Note, Tweet, MediaMetadata)
        .join(Tweet, Note.tweet_id == Tweet.tweet_id)
        .outerjoin(MediaMetadata, Tweet.tweet_id == MediaMetadata.tweet_id)
        .filter(Note.is_media_note == True)
    )
    
    if output_limit:
        query = query.limit(output_limit)
    
    samples = []
    for note, tweet, media in query.all():
        sample = {
            "video": {
                "filename": media.local_path.split("/")[-1] if media and media.local_path else None,
                "duration_seconds": media.duration_ms / 1000 if media and media.duration_ms else None,
                "path": media.local_path if media else None,
                "title": media.title if media else None,
                "uploader": media.uploader if media else None,
            },
            "tweet": {
                "tweet_id": str(tweet.tweet_id),
                "url": f"https://twitter.com/i/status/{tweet.tweet_id}",
                "text": tweet.text,
                "author_name": tweet.author_name,
                "author_username": tweet.author_username,
                "author_verified": tweet.author_verified,
                "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                "engagement": {
                    "likes": tweet.likes,
                    "retweets": tweet.retweets,
                    "replies": tweet.replies,
                    "views": 0  # Not available
                }
            },
            "community_note": {
                "note_id": str(note.note_id),
                "classification": note.classification,
                "summary": note.summary,
                "is_misleading": note.classification == "MISINFORMED_OR_POTENTIALLY_MISLEADING",
                "created_at_millis": note.created_at_millis,
                "reasons": {
                    "factual_error": note.misleading_factual_error,
                    "manipulated_media": note.misleading_manipulated_media,
                    "missing_context": note.misleading_missing_important_context,
                    "outdated_info": note.misleading_outdated_information,
                }
            }
        }
        samples.append(sample)
    
    return samples


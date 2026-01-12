"""
SQLAlchemy models for video LLM evaluation database.

Tables:
- notes: Community Notes data from raw TSV files
- tweets: Tweet data with Twitter API information
- media_metadata: yt-dlp scraped metadata for videos and images
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from database.config import Base


class Note(Base):
    """
    Community Notes table - stores all 23 columns from raw TSV files.
    
    Multiple notes can reference the same tweet (one-to-many relationship).
    """
    
    __tablename__ = "notes"
    
    # Primary key
    note_id = Column(BigInteger, primary_key=True, index=True)
    
    # Foreign key to tweets
    tweet_id = Column(BigInteger, ForeignKey("tweets.tweet_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Note metadata
    note_author_participant_id = Column(String(255), nullable=False)
    created_at_millis = Column(BigInteger, nullable=False)
    
    # Classification
    classification = Column(String(100), nullable=True, index=True)
    believable = Column(String(50), nullable=True)
    harmful = Column(String(50), nullable=True)
    validation_difficulty = Column(String(50), nullable=True)
    
    # Misleading reason flags (10 columns)
    misleading_other = Column(Integer, nullable=True)
    misleading_factual_error = Column(Integer, nullable=True)
    misleading_manipulated_media = Column(Integer, nullable=True)
    misleading_outdated_information = Column(Integer, nullable=True)
    misleading_missing_important_context = Column(Integer, nullable=True)
    misleading_unverified_claim_as_fact = Column(Integer, nullable=True)
    misleading_satire = Column(Integer, nullable=True)
    
    # Not misleading reason flags (5 columns)
    not_misleading_other = Column(Integer, nullable=True)
    not_misleading_factually_correct = Column(Integer, nullable=True)
    not_misleading_outdated_but_not_when_written = Column(Integer, nullable=True)
    not_misleading_clearly_satire = Column(Integer, nullable=True)
    not_misleading_personal_opinion = Column(Integer, nullable=True)
    
    # Additional metadata
    trustworthy_sources = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    is_media_note = Column(Boolean, nullable=True, index=True)
    
    # URL for direct access to note on Twitter
    note_url = Column(String(500), nullable=True)
    
    # Note status fields (from noteStatusHistory)
    current_status = Column(String(100), nullable=True, index=True)
    first_non_nmr_status = Column(String(100), nullable=True)
    most_recent_non_nmr_status = Column(String(100), nullable=True)
    
    # Relationships
    tweet = relationship("Tweet", back_populates="notes")
    
    def __repr__(self):
        return f"<Note(note_id={self.note_id}, tweet_id={self.tweet_id}, classification={self.classification})>"


class Tweet(Base):
    """
    Tweets table - stores tweet data and Twitter API information.
    
    Central linking table for all tweet-related data.
    """
    
    __tablename__ = "tweets"
    
    # Primary key
    tweet_id = Column(BigInteger, primary_key=True, index=True)
    
    # Tweet content
    text = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True, index=True)
    
    # Author information
    author_id = Column(String(100), nullable=True)
    author_name = Column(String(255), nullable=True)
    author_username = Column(String(255), nullable=True)
    author_verified = Column(Boolean, nullable=True)
    
    # Engagement metrics
    likes = Column(Integer, nullable=True, index=True)
    retweets = Column(Integer, nullable=True)
    replies = Column(Integer, nullable=True)
    quotes = Column(Integer, nullable=True)
    
    # Media flags
    is_verified_video = Column(Boolean, nullable=True, index=True)
    media_type = Column(String(50), nullable=True, index=True)
    
    # Raw API data (JSONB for complete data preservation)
    raw_api_data = Column(JSONB, nullable=True)
    api_fetched_at = Column(DateTime, nullable=True)
    
    # URL for direct access to tweet on Twitter/X
    tweet_url = Column(String(500), nullable=True)
    
    # Relationships
    notes = relationship("Note", back_populates="tweet", cascade="all, delete-orphan")
    media_metadata = relationship("MediaMetadata", back_populates="tweet", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tweet(tweet_id={self.tweet_id}, author={self.author_username}, likes={self.likes})>"


class MediaMetadata(Base):
    """
    Media metadata table - stores yt-dlp scraped metadata for videos and images.
    
    One-to-one relationship with tweets.
    """
    
    __tablename__ = "media_metadata"
    
    # Primary key and foreign key (one-to-one)
    tweet_id = Column(BigInteger, ForeignKey("tweets.tweet_id", ondelete="CASCADE"), primary_key=True, index=True)
    
    # Media identification
    media_id = Column(String(255), nullable=True)
    media_type = Column(String(50), nullable=True, index=True)  # 'video' or 'image'
    
    # Media content
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    
    # Uploader information
    uploader = Column(String(255), nullable=True)
    uploader_id = Column(String(255), nullable=True)
    
    # Media technical details
    timestamp = Column(Integer, nullable=True)  # Unix timestamp
    duration_ms = Column(Integer, nullable=True)  # NULL for images
    like_count = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Complex data as JSONB
    formats = Column(JSONB, nullable=True)  # Complete format information from yt-dlp
    
    # Local storage
    local_path = Column(String(500), nullable=True)
    
    # Relationships
    tweet = relationship("Tweet", back_populates="media_metadata")
    
    def __repr__(self):
        return f"<MediaMetadata(tweet_id={self.tweet_id}, media_type={self.media_type}, duration_ms={self.duration_ms})>"


# Create indexes for common queries
Index("idx_notes_classification", Note.classification)
Index("idx_notes_tweet_id", Note.tweet_id)
Index("idx_tweets_likes", Tweet.likes)
Index("idx_tweets_media_type", Tweet.media_type)
Index("idx_media_metadata_type", MediaMetadata.media_type)


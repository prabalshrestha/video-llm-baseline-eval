"""Initial migration: create notes, tweets, and media_metadata tables

Revision ID: fc64cda72ac3
Revises: 
Create Date: 2025-12-17 00:53:41.186265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fc64cda72ac3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create all tables."""
    
    # Create tweets table first (no foreign keys)
    op.create_table(
        'tweets',
        sa.Column('tweet_id', sa.BigInteger(), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('author_id', sa.String(length=100), nullable=True),
        sa.Column('author_name', sa.String(length=255), nullable=True),
        sa.Column('author_username', sa.String(length=255), nullable=True),
        sa.Column('author_verified', sa.Boolean(), nullable=True),
        sa.Column('likes', sa.Integer(), nullable=True),
        sa.Column('retweets', sa.Integer(), nullable=True),
        sa.Column('replies', sa.Integer(), nullable=True),
        sa.Column('quotes', sa.Integer(), nullable=True),
        sa.Column('is_verified_video', sa.Boolean(), nullable=True),
        sa.Column('media_type', sa.String(length=50), nullable=True),
        sa.Column('raw_api_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('api_fetched_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('tweet_id')
    )
    
    # Create indexes on tweets table
    op.create_index('idx_tweets_likes', 'tweets', ['likes'])
    op.create_index('idx_tweets_media_type', 'tweets', ['media_type'])
    op.create_index(op.f('ix_tweets_created_at'), 'tweets', ['created_at'])
    op.create_index(op.f('ix_tweets_is_verified_video'), 'tweets', ['is_verified_video'])
    op.create_index(op.f('ix_tweets_tweet_id'), 'tweets', ['tweet_id'])
    
    # Create notes table (references tweets)
    op.create_table(
        'notes',
        sa.Column('note_id', sa.BigInteger(), nullable=False),
        sa.Column('tweet_id', sa.BigInteger(), nullable=False),
        sa.Column('note_author_participant_id', sa.String(length=255), nullable=False),
        sa.Column('created_at_millis', sa.BigInteger(), nullable=False),
        sa.Column('classification', sa.String(length=100), nullable=True),
        sa.Column('believable', sa.String(length=50), nullable=True),
        sa.Column('harmful', sa.String(length=50), nullable=True),
        sa.Column('validation_difficulty', sa.String(length=50), nullable=True),
        sa.Column('misleading_other', sa.Integer(), nullable=True),
        sa.Column('misleading_factual_error', sa.Integer(), nullable=True),
        sa.Column('misleading_manipulated_media', sa.Integer(), nullable=True),
        sa.Column('misleading_outdated_information', sa.Integer(), nullable=True),
        sa.Column('misleading_missing_important_context', sa.Integer(), nullable=True),
        sa.Column('misleading_unverified_claim_as_fact', sa.Integer(), nullable=True),
        sa.Column('misleading_satire', sa.Integer(), nullable=True),
        sa.Column('not_misleading_other', sa.Integer(), nullable=True),
        sa.Column('not_misleading_factually_correct', sa.Integer(), nullable=True),
        sa.Column('not_misleading_outdated_but_not_when_written', sa.Integer(), nullable=True),
        sa.Column('not_misleading_clearly_satire', sa.Integer(), nullable=True),
        sa.Column('not_misleading_personal_opinion', sa.Integer(), nullable=True),
        sa.Column('trustworthy_sources', sa.Integer(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('is_media_note', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['tweet_id'], ['tweets.tweet_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('note_id')
    )
    
    # Create indexes on notes table
    op.create_index('idx_notes_classification', 'notes', ['classification'])
    op.create_index('idx_notes_tweet_id', 'notes', ['tweet_id'])
    op.create_index(op.f('ix_notes_is_media_note'), 'notes', ['is_media_note'])
    op.create_index(op.f('ix_notes_note_id'), 'notes', ['note_id'])
    
    # Create media_metadata table (references tweets)
    op.create_table(
        'media_metadata',
        sa.Column('tweet_id', sa.BigInteger(), nullable=False),
        sa.Column('media_id', sa.String(length=255), nullable=True),
        sa.Column('media_type', sa.String(length=50), nullable=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('uploader', sa.String(length=255), nullable=True),
        sa.Column('uploader_id', sa.String(length=255), nullable=True),
        sa.Column('timestamp', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('like_count', sa.Integer(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('formats', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('local_path', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['tweet_id'], ['tweets.tweet_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tweet_id')
    )
    
    # Create indexes on media_metadata table
    op.create_index('idx_media_metadata_type', 'media_metadata', ['media_type'])
    op.create_index(op.f('ix_media_metadata_tweet_id'), 'media_metadata', ['tweet_id'])


def downgrade() -> None:
    """Downgrade schema: drop all tables."""
    
    # Drop tables in reverse order (child tables first)
    op.drop_index(op.f('ix_media_metadata_tweet_id'), table_name='media_metadata')
    op.drop_index('idx_media_metadata_type', table_name='media_metadata')
    op.drop_table('media_metadata')
    
    op.drop_index(op.f('ix_notes_note_id'), table_name='notes')
    op.drop_index(op.f('ix_notes_is_media_note'), table_name='notes')
    op.drop_index('idx_notes_tweet_id', table_name='notes')
    op.drop_index('idx_notes_classification', table_name='notes')
    op.drop_table('notes')
    
    op.drop_index(op.f('ix_tweets_tweet_id'), table_name='tweets')
    op.drop_index(op.f('ix_tweets_is_verified_video'), table_name='tweets')
    op.drop_index(op.f('ix_tweets_created_at'), table_name='tweets')
    op.drop_index('idx_tweets_media_type', table_name='tweets')
    op.drop_index('idx_tweets_likes', table_name='tweets')
    op.drop_table('tweets')

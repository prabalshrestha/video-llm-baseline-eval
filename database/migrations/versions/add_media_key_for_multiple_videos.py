"""add media_key for multiple videos per tweet

Revision ID: add_media_key_multi
Revises: 97b67d0f69ca
Create Date: 2026-01-21 00:00:00.000000

This migration updates MediaMetadata to support multiple videos per tweet:
1. Adds media_key column (unique identifier for each video)
2. Adds video_index column (sequence number for videos in the same tweet)
3. Changes primary key from tweet_id to media_key
4. Keeps tweet_id as foreign key (one-to-many relationship)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_media_key_multi'
down_revision = '97b67d0f69ca'
branch_labels = None
depends_on = None


def upgrade():
    """
    Upgrade database schema to support multiple videos per tweet.
    
    WARNING: Run fix_video_mapping.py BEFORE running this migration!
    """
    # Step 1: Add new columns (nullable first to allow existing data)
    op.add_column('media_metadata', 
        sa.Column('media_key', sa.String(length=255), nullable=True))
    op.add_column('media_metadata', 
        sa.Column('video_index', sa.Integer(), nullable=True, default=1))
    
    # Step 2: Populate media_key and video_index for existing records
    # Format: {tweet_id}_{video_index}
    # This SQL assumes all existing records are the first video (index=1)
    op.execute("""
        UPDATE media_metadata 
        SET media_key = tweet_id::text || '_1',
            video_index = 1
        WHERE media_key IS NULL
    """)
    
    # Step 3: Make columns non-nullable now that they're populated
    op.alter_column('media_metadata', 'media_key', nullable=False)
    op.alter_column('media_metadata', 'video_index', nullable=False)
    
    # Step 4: Drop existing primary key constraint
    op.drop_constraint('media_metadata_pkey', 'media_metadata', type_='primary')
    
    # Step 5: Create new primary key on media_key
    op.create_primary_key('media_metadata_pkey', 'media_metadata', ['media_key'])
    
    # Step 6: Create index on tweet_id for foreign key lookups
    op.create_index('idx_media_metadata_tweet_id', 'media_metadata', ['tweet_id'])
    
    # Step 7: Create unique constraint to prevent duplicate video_index per tweet
    op.create_unique_constraint(
        'uq_media_metadata_tweet_video_idx', 
        'media_metadata', 
        ['tweet_id', 'video_index']
    )
    
    # Step 8: Add index on video_index for ordering queries
    op.create_index('idx_media_metadata_video_index', 'media_metadata', ['video_index'])


def downgrade():
    """
    Downgrade to single video per tweet (one-to-one relationship).
    
    WARNING: This will DELETE all videos except the first one for each tweet!
    """
    # Step 1: Delete all videos except video_index=1
    op.execute("""
        DELETE FROM media_metadata 
        WHERE video_index > 1
    """)
    
    # Step 2: Drop indexes and constraints
    op.drop_index('idx_media_metadata_video_index', table_name='media_metadata')
    op.drop_constraint('uq_media_metadata_tweet_video_idx', 'media_metadata', type_='unique')
    op.drop_index('idx_media_metadata_tweet_id', table_name='media_metadata')
    
    # Step 3: Drop current primary key
    op.drop_constraint('media_metadata_pkey', 'media_metadata', type_='primary')
    
    # Step 4: Recreate primary key on tweet_id
    op.create_primary_key('media_metadata_pkey', 'media_metadata', ['tweet_id'])
    
    # Step 5: Drop new columns
    op.drop_column('media_metadata', 'video_index')
    op.drop_column('media_metadata', 'media_key')

"""Add URL columns to tweets and notes tables

Revision ID: 015f90d23a27
Revises: fc64cda72ac3
Create Date: 2026-01-08 00:34:32.090994

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '015f90d23a27'
down_revision: Union[str, Sequence[str], None] = 'fc64cda72ac3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add tweet_url column to tweets table
    op.add_column('tweets', sa.Column('tweet_url', sa.String(length=500), nullable=True))
    
    # Add note_url column to notes table
    op.add_column('notes', sa.Column('note_url', sa.String(length=500), nullable=True))
    
    # Optionally populate URLs for existing rows using SQL expressions
    # For tweets: https://twitter.com/i/status/{tweet_id}
    op.execute("UPDATE tweets SET tweet_url = 'https://twitter.com/i/status/' || tweet_id WHERE tweet_url IS NULL")
    
    # For notes: https://twitter.com/i/birdwatch/n/{note_id}
    op.execute("UPDATE notes SET note_url = 'https://twitter.com/i/birdwatch/n/' || note_id WHERE note_url IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the URL columns
    op.drop_column('notes', 'note_url')
    op.drop_column('tweets', 'tweet_url')

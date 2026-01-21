"""add_note_status_fields

Revision ID: 97b67d0f69ca
Revises: 015f90d23a27
Create Date: 2026-01-12 12:28:20.285261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97b67d0f69ca'
down_revision: Union[str, Sequence[str], None] = '015f90d23a27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add note status fields."""
    # Add status columns to notes table
    op.add_column('notes', sa.Column('current_status', sa.String(length=100), nullable=True))
    op.add_column('notes', sa.Column('first_non_nmr_status', sa.String(length=100), nullable=True))
    op.add_column('notes', sa.Column('most_recent_non_nmr_status', sa.String(length=100), nullable=True))
    
    # Create index on current_status for faster filtering
    op.create_index('idx_notes_current_status', 'notes', ['current_status'], unique=False)


def downgrade() -> None:
    """Downgrade schema: Remove note status fields."""
    # Drop index first
    op.drop_index('idx_notes_current_status', table_name='notes')
    
    # Drop columns
    op.drop_column('notes', 'most_recent_non_nmr_status')
    op.drop_column('notes', 'first_non_nmr_status')
    op.drop_column('notes', 'current_status')

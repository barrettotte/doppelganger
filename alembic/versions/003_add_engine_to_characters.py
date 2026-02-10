"""Add engine column to characters table.

Revision ID: 003
Revises: 002
Create Date: 2026-02-10
"""

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add engine column defaulting to chatterbox for existing rows."""
    op.execute("ALTER TABLE characters ADD COLUMN engine VARCHAR(20) NOT NULL DEFAULT 'chatterbox'")


def downgrade() -> None:
    """Remove engine column."""
    op.execute("ALTER TABLE characters DROP COLUMN IF EXISTS engine")

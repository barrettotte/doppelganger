"""Add username column to users table.

Revision ID: 002
Revises: 001
Create Date: 2026-02-09
"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN username VARCHAR(100)")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS username")

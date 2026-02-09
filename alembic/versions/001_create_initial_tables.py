"""Create initial tables: users, characters, tts_requests, audit_log.

Revision ID: 001
Revises:
Create Date: 2026-02-08
"""

from pathlib import Path

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

_here = Path(__file__).parent


def upgrade() -> None:
    sql = (_here / "001_create_initial_tables.sql").read_text()
    op.execute(sql)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log")
    op.execute("DROP TABLE IF EXISTS tts_requests")
    op.execute("DROP TABLE IF EXISTS characters")
    op.execute("DROP TABLE IF EXISTS users")

"""Add admin consultation note to estimates.

Revision ID: 0008_admin_consultation_note
Revises: 0007_estimate_questions
Create Date: 2026-09-05 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0008_admin_consultation_note"
down_revision: str | Sequence[str] | None = "0007_estimate_questions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("estimates", sa.Column("admin_consultation_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("estimates", "admin_consultation_note")


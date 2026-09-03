"""Add customer questionnaire fields to estimates.

Revision ID: 0007_estimate_questions
Revises: 0006_estimate_shares
Create Date: 2026-09-03 00:00:02.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0007_estimate_questions"
down_revision: str | Sequence[str] | None = "0006_estimate_shares"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("estimates", sa.Column("customer_email", sa.String(length=255), nullable=True))
    op.add_column("estimates", sa.Column("housing_type", sa.String(length=50), nullable=True))
    op.add_column("estimates", sa.Column("floor_area_pyeong", sa.Numeric(precision=8, scale=2), nullable=True))
    op.add_column("estimates", sa.Column("renovation_scope", sa.String(length=50), nullable=True))
    op.add_column("estimates", sa.Column("preferred_timeline", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("estimates", "preferred_timeline")
    op.drop_column("estimates", "renovation_scope")
    op.drop_column("estimates", "floor_area_pyeong")
    op.drop_column("estimates", "housing_type")
    op.drop_column("estimates", "customer_email")

"""Add estimate shares.

Revision ID: 0006_estimate_shares
Revises: 0005_admin_users
Create Date: 2026-09-03 00:00:01.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0006_estimate_shares"
down_revision: str | Sequence[str] | None = "0005_admin_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "estimate_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("estimate_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("access_count >= 0", name="ck_estimate_shares_access_count_non_negative"),
        sa.ForeignKeyConstraint(["estimate_id"], ["estimates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_estimate_shares_id"), "estimate_shares", ["id"], unique=False)
    op.create_index(op.f("ix_estimate_shares_estimate_id"), "estimate_shares", ["estimate_id"], unique=False)
    op.create_index(op.f("ix_estimate_shares_expires_at"), "estimate_shares", ["expires_at"], unique=False)
    op.create_index(
        "uq_estimate_shares_active_estimate",
        "estimate_shares",
        ["estimate_id"],
        unique=True,
        postgresql_where=sa.text("active IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index("uq_estimate_shares_active_estimate", table_name="estimate_shares")
    op.drop_index(op.f("ix_estimate_shares_expires_at"), table_name="estimate_shares")
    op.drop_index(op.f("ix_estimate_shares_estimate_id"), table_name="estimate_shares")
    op.drop_index(op.f("ix_estimate_shares_id"), table_name="estimate_shares")
    op.drop_table("estimate_shares")

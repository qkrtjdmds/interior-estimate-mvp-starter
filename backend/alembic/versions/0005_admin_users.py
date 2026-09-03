"""Add admin users.

Revision ID: 0005_admin_users
Revises: 0004_estimate_constraints
Create Date: 2026-09-03 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_admin_users"
down_revision: str | Sequence[str] | None = "0004_estimate_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_users_id"), "admin_users", ["id"], unique=False)
    op.create_index("ix_admin_users_active", "admin_users", ["active"], unique=False)
    op.create_index(
        "uq_admin_users_normalized_email",
        "admin_users",
        [sa.text("lower(btrim(email))")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_admin_users_normalized_email", table_name="admin_users")
    op.drop_index("ix_admin_users_active", table_name="admin_users")
    op.drop_index(op.f("ix_admin_users_id"), table_name="admin_users")
    op.drop_table("admin_users")

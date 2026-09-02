"""Add estimates and estimate items.

Revision ID: 0003_estimates_items
Revises: 0002_reference_normalized_unique
Create Date: 2026-09-02 00:00:02.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_estimates_items"
down_revision: str | Sequence[str] | None = "0002_reference_normalized_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "estimates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("estimate_number", sa.String(length=40), nullable=False),
        sa.Column("customer_name", sa.String(length=100), nullable=False),
        sa.Column("customer_phone", sa.String(length=50), nullable=True),
        sa.Column("project_address", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("vat_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("vat_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("estimate_number"),
    )
    op.create_index(op.f("ix_estimates_created_at"), "estimates", ["created_at"], unique=False)
    op.create_index(op.f("ix_estimates_estimate_number"), "estimates", ["estimate_number"], unique=False)
    op.create_index(op.f("ix_estimates_id"), "estimates", ["id"], unique=False)
    op.create_index(op.f("ix_estimates_status"), "estimates", ["status"], unique=False)

    op.create_table(
        "estimate_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("estimate_id", sa.Integer(), nullable=False),
        sa.Column("option_id", sa.Integer(), nullable=True),
        sa.Column("category_name_snapshot", sa.String(length=100), nullable=False),
        sa.Column("item_name_snapshot", sa.String(length=100), nullable=False),
        sa.Column("option_name_snapshot", sa.String(length=100), nullable=False),
        sa.Column("description_snapshot", sa.Text(), nullable=True),
        sa.Column("unit_snapshot", sa.String(length=20), nullable=False),
        sa.Column("unit_price_snapshot", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["estimate_id"], ["estimates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["option_id"], ["options.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_estimate_items_estimate_sort_id", "estimate_items", ["estimate_id", "sort_order", "id"], unique=False)
    op.create_index(op.f("ix_estimate_items_estimate_id"), "estimate_items", ["estimate_id"], unique=False)
    op.create_index(op.f("ix_estimate_items_id"), "estimate_items", ["id"], unique=False)
    op.create_index(op.f("ix_estimate_items_option_id"), "estimate_items", ["option_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_estimate_items_option_id"), table_name="estimate_items")
    op.drop_index(op.f("ix_estimate_items_id"), table_name="estimate_items")
    op.drop_index(op.f("ix_estimate_items_estimate_id"), table_name="estimate_items")
    op.drop_index("ix_estimate_items_estimate_sort_id", table_name="estimate_items")
    op.drop_table("estimate_items")
    op.drop_index(op.f("ix_estimates_status"), table_name="estimates")
    op.drop_index(op.f("ix_estimates_id"), table_name="estimates")
    op.drop_index(op.f("ix_estimates_estimate_number"), table_name="estimates")
    op.drop_index(op.f("ix_estimates_created_at"), table_name="estimates")
    op.drop_table("estimates")
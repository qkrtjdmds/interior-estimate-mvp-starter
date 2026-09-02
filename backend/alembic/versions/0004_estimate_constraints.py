"""Add estimate integrity constraints.

Revision ID: 0004_estimate_constraints
Revises: 0003_estimates_items
Create Date: 2026-09-02 00:00:03.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004_estimate_constraints"
down_revision: str | Sequence[str] | None = "0003_estimates_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint("ck_estimates_subtotal_non_negative", "estimates", "subtotal >= 0")
    op.create_check_constraint("ck_estimates_vat_rate_non_negative", "estimates", "vat_rate >= 0")
    op.create_check_constraint("ck_estimates_vat_amount_non_negative", "estimates", "vat_amount >= 0")
    op.create_check_constraint("ck_estimates_total_amount_non_negative", "estimates", "total_amount >= 0")
    op.create_check_constraint("ck_estimate_items_quantity_positive", "estimate_items", "quantity > 0")
    op.create_check_constraint("ck_estimate_items_line_total_non_negative", "estimate_items", "line_total >= 0")
    op.create_index(
        "uq_estimate_items_estimate_option",
        "estimate_items",
        ["estimate_id", "option_id"],
        unique=True,
        postgresql_where=sa.text("option_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_estimate_items_estimate_option", table_name="estimate_items")
    op.drop_constraint("ck_estimate_items_line_total_non_negative", "estimate_items", type_="check")
    op.drop_constraint("ck_estimate_items_quantity_positive", "estimate_items", type_="check")
    op.drop_constraint("ck_estimates_total_amount_non_negative", "estimates", type_="check")
    op.drop_constraint("ck_estimates_vat_amount_non_negative", "estimates", type_="check")
    op.drop_constraint("ck_estimates_vat_rate_non_negative", "estimates", type_="check")
    op.drop_constraint("ck_estimates_subtotal_non_negative", "estimates", type_="check")
"""Add normalized reference unique indexes.

Revision ID: 0002_reference_normalized_unique
Revises: 0001_reference_baseline
Create Date: 2026-09-02 00:00:01.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_reference_normalized_unique"
down_revision: str | Sequence[str] | None = "0001_reference_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_categories_normalized_name",
        "categories",
        [sa.text("lower(btrim(name))")],
        unique=True,
    )
    op.create_index(
        "uq_items_category_normalized_name",
        "items",
        ["category_id", sa.text("lower(btrim(name))")],
        unique=True,
    )
    op.create_index(
        "uq_options_item_normalized_name",
        "options",
        ["item_id", sa.text("lower(btrim(name))")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_options_item_normalized_name", table_name="options")
    op.drop_index("uq_items_category_normalized_name", table_name="items")
    op.drop_index("uq_categories_normalized_name", table_name="categories")
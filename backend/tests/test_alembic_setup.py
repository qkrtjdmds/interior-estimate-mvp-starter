from pathlib import Path

from alembic.config import Config

from app.db.base import Base
from app.models import AdminUser, Category, Estimate, EstimateItem, EstimateShare, Item, Option  # noqa: F401


def test_metadata_contains_reference_tables() -> None:
    assert {"categories", "items", "options"}.issubset(Base.metadata.tables.keys())


def test_alembic_config_does_not_hardcode_database_url() -> None:
    config = Config("alembic.ini")
    assert config.get_main_option("script_location") == "alembic"
    assert config.get_main_option("sqlalchemy.url") in (None, "")


def test_migration_files_define_reference_revisions() -> None:
    versions = Path("alembic/versions")
    baseline = (versions / "0001_reference_baseline.py").read_text(encoding="ascii")
    unique = (versions / "0002_reference_normalized_unique.py").read_text(encoding="ascii")

    assert "0001_reference_baseline" in baseline
    assert "create_table" in baseline
    assert "categories" in baseline
    assert "items" in baseline
    assert "options" in baseline
    assert "0002_reference_normalized_unique" in unique
    assert "uq_categories_normalized_name" in unique
    assert "uq_items_category_normalized_name" in unique
    assert "uq_options_item_normalized_name" in unique

def test_estimate_migration_file_defines_revision() -> None:
    migration = (Path("alembic/versions") / "0003_estimates_items.py").read_text(encoding="ascii")

    assert "0003_estimates_items" in migration
    assert "estimates" in migration
    assert "estimate_items" in migration
    assert "ondelete=\"SET NULL\"" in migration


def test_estimate_constraints_migration_file_defines_revision() -> None:
    migration = (Path("alembic/versions") / "0004_estimate_constraints.py").read_text(encoding="ascii")

    assert "0004_estimate_constraints" in migration
    assert "ck_estimate_items_quantity_positive" in migration
    assert "ck_estimates_subtotal_non_negative" in migration
    assert "uq_estimate_items_estimate_option" in migration
    assert "option_id IS NOT NULL" in migration


def test_admin_users_migration_file_defines_revision() -> None:
    migration = (Path("alembic/versions") / "0005_admin_users.py").read_text(encoding="ascii")

    assert "0005_admin_users" in migration
    assert "0004_estimate_constraints" in migration
    assert "admin_users" in migration
    assert "password_hash" in migration
    assert "uq_admin_users_normalized_email" in migration
    assert "lower(btrim(email))" in migration


def test_estimate_shares_migration_file_defines_revision() -> None:
    migration = (Path("alembic/versions") / "0006_estimate_shares.py").read_text(encoding="ascii")

    assert "0006_estimate_shares" in migration
    assert "0005_admin_users" in migration
    assert "estimate_shares" in migration
    assert "token_hash" in migration
    assert "uq_estimate_shares_active_estimate" in migration
    assert "active IS TRUE" in migration

def test_admin_consultation_note_migration_file_defines_revision() -> None:
    migration = (Path("alembic/versions") / "0008_admin_consultation_note.py").read_text(encoding="ascii")

    assert "0008_admin_consultation_note" in migration
    assert "0007_estimate_questions" in migration
    assert "admin_consultation_note" in migration

import os
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest
from sqlalchemy import func, select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.seed_reference_data import REFERENCE_DATA, seed_reference_data
from app.models import Category, Item, Option  # noqa: F401

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def count_rows(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_seed_creates_reference_data_in_empty_db() -> None:
    with TestingSessionLocal() as db:
        summary = seed_reference_data(db)

        assert summary.categories_created == 7
        assert summary.items_created == 9
        assert summary.options_created == 17
        assert count_rows(db, Category) == 7
        assert count_rows(db, Item) == 9
        assert count_rows(db, Option) == 17

        wallpaper = db.scalar(select(Item).join(Category).where(Category.name == "도배", Item.name == "벽지 시공"))
        assert wallpaper is not None

        silk = db.scalar(select(Option).where(Option.item_id == wallpaper.id, Option.name == "실크벽지"))
        assert silk is not None
        assert silk.unit == "평"
        assert silk.default_price == Decimal("45000.00")
        assert silk.recommended is True


def test_seed_is_idempotent() -> None:
    with TestingSessionLocal() as db:
        first = seed_reference_data(db)
        second = seed_reference_data(db)

        assert first.categories_created == 7
        assert second.categories_created == 0
        assert second.categories_skipped == 7
        assert second.items_created == 0
        assert second.items_skipped == 9
        assert second.options_created == 0
        assert second.options_skipped == 17
        assert count_rows(db, Category) == 7
        assert count_rows(db, Item) == 9
        assert count_rows(db, Option) == 17


def test_seed_reuses_existing_category_and_does_not_overwrite_existing_price() -> None:
    with TestingSessionLocal() as db:
        category = Category(name=" 도배 ", description="custom category", active=False, customer_visible=False, sort_order=999)
        db.add(category)
        db.flush()
        item = Item(category_id=category.id, name="벽지 시공", description="custom item")
        db.add(item)
        db.flush()
        option = Option(
            item_id=item.id,
            name="실크벽지",
            description="custom option",
            unit="평",
            default_price=Decimal("1.00"),
            recommended=False,
        )
        db.add(option)
        db.commit()

        summary = seed_reference_data(db)
        db.refresh(category)
        db.refresh(option)

        assert summary.categories_created == 6
        assert summary.categories_skipped == 1
        assert category.description == "custom category"
        assert category.active is False
        assert category.sort_order == 999
        assert option.default_price == Decimal("1.00")
        assert option.description == "custom option"
        assert option.recommended is False


def test_seed_parent_child_relationships_are_correct() -> None:
    with TestingSessionLocal() as db:
        seed_reference_data(db)

        for category_data in REFERENCE_DATA:
            category = db.scalar(select(Category).where(Category.name == category_data["name"]))
            assert category is not None
            for item_data in category_data["items"]:
                item = db.scalar(select(Item).where(Item.category_id == category.id, Item.name == item_data["name"]))
                assert item is not None
                for option_data in item_data["options"]:
                    option = db.scalar(select(Option).where(Option.item_id == item.id, Option.name == option_data["name"]))
                    assert option is not None
                    assert option.unit == option_data["unit"]
                    assert option.default_price == option_data["default_price"]


def test_seed_rolls_back_on_error() -> None:
    broken_seed = [
        {
            "name": "Rollback Category",
            "description": "This should not remain after failure.",
            "items": [
                {
                    "description": "Missing name raises an error after category flush.",
                    "options": [],
                }
            ],
        }
    ]

    with TestingSessionLocal() as db:
        with pytest.raises(KeyError):
            seed_reference_data(db, broken_seed)

        assert count_rows(db, Category) == 0
        assert count_rows(db, Item) == 0
        assert count_rows(db, Option) == 0
import os
from collections.abc import Generator
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AdminUser, Category, Estimate, EstimateItem, Item, Option  # noqa: F401

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
client = TestClient(app)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_function() -> None:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def add_reference(
    *,
    category_name: str,
    item_name: str,
    option_name: str,
    category_sort: int = 0,
    item_sort: int = 0,
    option_sort: int = 0,
    category_active: bool = True,
    category_visible: bool = True,
    item_active: bool = True,
    item_visible: bool = True,
    option_active: bool = True,
    option_visible: bool = True,
    recommended: bool = False,
) -> None:
    with TestingSessionLocal() as db:
        category = Category(
            name=category_name,
            description=f"{category_name} description",
            sort_order=category_sort,
            active=category_active,
            customer_visible=category_visible,
        )
        db.add(category)
        db.flush()
        item = Item(
            category_id=category.id,
            name=item_name,
            description=f"{item_name} description",
            sort_order=item_sort,
            active=item_active,
            customer_visible=item_visible,
        )
        db.add(item)
        db.flush()
        db.add(
            Option(
                item_id=item.id,
                name=option_name,
                description=f"{option_name} description",
                unit="평",
                default_price=Decimal("123.45"),
                recommended=recommended,
                sort_order=option_sort,
                active=option_active,
                customer_visible=option_visible,
            )
        )
        db.commit()


def test_catalog_returns_visible_active_tree_sorted() -> None:
    add_reference(category_name="B", item_name="B Item", option_name="B Option", category_sort=2, item_sort=1, option_sort=1)
    add_reference(category_name="A", item_name="A Item", option_name="A Option", category_sort=1, item_sort=1, option_sort=1, recommended=True)

    response = client.get("/api/catalog")

    assert response.status_code == 200
    body = response.json()
    assert [category["name"] for category in body] == ["A", "B"]
    assert body[0]["items"][0]["options"][0]["name"] == "A Option"
    assert body[0]["items"][0]["options"][0]["recommended"] is True
    assert Decimal(str(body[0]["items"][0]["options"][0]["default_price"])) == Decimal("123.45")


def test_catalog_filters_hidden_or_inactive_parent_chain() -> None:
    add_reference(category_name="Visible", item_name="Visible Item", option_name="Visible Option")
    add_reference(category_name="Inactive Category", item_name="Item", option_name="Option", category_active=False)
    add_reference(category_name="Hidden Category", item_name="Item", option_name="Option", category_visible=False)
    add_reference(category_name="Inactive Item", item_name="Item", option_name="Option", item_active=False)
    add_reference(category_name="Hidden Item", item_name="Item", option_name="Option", item_visible=False)
    add_reference(category_name="Inactive Option", item_name="Item", option_name="Option", option_active=False)
    add_reference(category_name="Hidden Option", item_name="Item", option_name="Option", option_visible=False)

    response = client.get("/api/catalog")

    assert response.status_code == 200
    body = response.json()
    assert [category["name"] for category in body] == ["Visible"]
    assert body[0]["items"][0]["options"][0]["name"] == "Visible Option"


def test_catalog_omits_admin_fields_and_empty_nodes() -> None:
    with TestingSessionLocal() as db:
        empty_category = Category(name="Empty", active=True, customer_visible=True)
        db.add(empty_category)
        hidden_option_category = Category(name="No Options", active=True, customer_visible=True)
        db.add(hidden_option_category)
        db.flush()
        item = Item(category_id=hidden_option_category.id, name="No Visible Options", active=True, customer_visible=True)
        db.add(item)
        db.flush()
        db.add(
            Option(
                item_id=item.id,
                name="Hidden",
                unit="개",
                default_price=Decimal("1.00"),
                active=True,
                customer_visible=False,
            )
        )
        db.commit()

    response = client.get("/api/catalog")

    assert response.status_code == 200
    assert response.json() == []

    add_reference(category_name="Visible", item_name="Visible Item", option_name="Visible Option")
    visible = client.get("/api/catalog").json()[0]
    assert "active" not in visible
    assert "customer_visible" not in visible
    assert "created_at" not in visible
    item_body = visible["items"][0]
    option_body = item_body["options"][0]
    assert "active" not in item_body
    assert "customer_visible" not in item_body
    assert "created_at" not in item_body
    assert "active" not in option_body
    assert "customer_visible" not in option_body
    assert "created_at" not in option_body


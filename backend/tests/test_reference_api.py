import os
import time
from collections.abc import Generator
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_admin
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AdminUser, Category, Item, Option  # noqa: F401

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_current_admin() -> object:
    return object()


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


def setup_function() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_admin] = override_get_current_admin
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_category_crud() -> None:
    created = client.post(
        "/api/categories",
        json={"name": "Floor", "description": "Floor work", "sort_order": 2},
    )
    assert created.status_code == 201
    category = created.json()
    assert category["name"] == "Floor"
    assert category["sort_order"] == 2
    assert category["created_at"]
    assert category["updated_at"]

    listed = client.get("/api/categories", params={"name": "flo"})
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [category["id"]]

    fetched = client.get(f"/api/categories/{category['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == category["id"]

    time.sleep(1.1)
    patched = client.patch(f"/api/categories/{category['id']}", json={"active": False, "sort_order": 1})
    assert patched.status_code == 200
    assert patched.json()["active"] is False
    assert patched.json()["sort_order"] == 1
    assert patched.json()["updated_at"] != category["updated_at"]

    deleted = client.delete(f"/api/categories/{category['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/categories/{category['id']}").status_code == 404


def test_missing_category_returns_404() -> None:
    assert client.get("/api/categories/999").status_code == 404


def test_item_create_checks_category_and_delete_conflict() -> None:
    missing_parent = client.post("/api/items", json={"category_id": 999, "name": "Paint"})
    assert missing_parent.status_code == 404

    category_id = client.post("/api/categories", json={"name": "Wall"}).json()["id"]
    item = client.post(
        "/api/items",
        json={"category_id": category_id, "name": "Paint", "sort_order": 3},
    )
    assert item.status_code == 201
    assert item.json()["category_id"] == category_id

    conflict = client.delete(f"/api/categories/{category_id}")
    assert conflict.status_code == 409


def test_option_create_checks_item_and_decimal_price() -> None:
    missing_parent = client.post(
        "/api/options",
        json={"item_id": 999, "name": "Basic", "unit": "m", "default_price": "123.45"},
    )
    assert missing_parent.status_code == 404

    category_id = client.post("/api/categories", json={"name": "Ceiling"}).json()["id"]
    item_id = client.post("/api/items", json={"category_id": category_id, "name": "Light"}).json()["id"]
    option = client.post(
        "/api/options",
        json={
            "item_id": item_id,
            "name": "LED",
            "unit": "개",
            "default_price": "123.45",
            "recommended": True,
        },
    )
    assert option.status_code == 201
    body = option.json()
    assert body["item_id"] == item_id
    assert Decimal(str(body["default_price"])) == Decimal("123.45")

    conflict = client.delete(f"/api/items/{item_id}")
    assert conflict.status_code == 409


def test_filters_and_sorting() -> None:
    first = client.post("/api/categories", json={"name": "B", "sort_order": 2, "active": True}).json()
    second = client.post("/api/categories", json={"name": "A", "sort_order": 1, "active": False}).json()

    listed = client.get("/api/categories")
    assert [row["id"] for row in listed.json()] == [second["id"], first["id"]]

    active_only = client.get("/api/categories", params={"active": True})
    assert [row["id"] for row in active_only.json()] == [first["id"]]


def test_validation_errors() -> None:
    assert client.post("/api/categories", json={"name": "   "}).status_code == 422
    assert client.post("/api/categories", json={"name": "Bad", "sort_order": -1}).status_code == 422
    assert client.post(
        "/api/options",
        json={"item_id": 1, "name": "Bad", "unit": "m", "default_price": "-1.00"},
    ).status_code == 422


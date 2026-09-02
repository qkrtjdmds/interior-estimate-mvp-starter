import os
from collections.abc import Generator
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.crud import estimate as estimate_crud
from app.models import Category, Estimate, EstimateItem, Item, Option  # noqa: F401

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


def create_option(name: str, price: str, *, active: bool = True) -> int:
    with TestingSessionLocal() as db:
        category = Category(name=f"Category {name}")
        db.add(category)
        db.flush()
        item = Item(category_id=category.id, name=f"Item {name}")
        db.add(item)
        db.flush()
        option = Option(
            item_id=item.id,
            name=name,
            description=f"Description {name}",
            unit="m",
            default_price=Decimal(price),
            active=active,
        )
        db.add(option)
        db.commit()
        return option.id


def test_create_estimate_success_and_unique_number() -> None:
    option_id = create_option("Paint", "100.00")

    response = client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": option_id, "quantity": "2.00"}]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["estimate_number"].startswith("EST-")
    assert body["status"] == "draft"
    assert Decimal(str(body["subtotal"])) == Decimal("200.00")
    assert Decimal(str(body["vat_rate"])) == Decimal("0.10")
    assert Decimal(str(body["vat_amount"])) == Decimal("20.00")
    assert Decimal(str(body["total_amount"])) == Decimal("220.00")
    assert body["items"][0]["option_name_snapshot"] == "Paint"
    assert body["items"][0]["unit_snapshot"] == "m"

    second = client.post(
        "/api/estimates",
        json={"customer_name": "Bob", "items": [{"option_id": option_id, "quantity": "1.00"}]},
    )
    assert second.status_code == 201
    assert second.json()["estimate_number"] != body["estimate_number"]


def test_multiple_items_total_and_rounding() -> None:
    option_a = create_option("A", "10.005")
    option_b = create_option("B", "20.00")

    response = client.post(
        "/api/estimates",
        json={
            "customer_name": "Alice",
            "items": [
                {"option_id": option_a, "quantity": "1.00", "sort_order": 2},
                {"option_id": option_b, "quantity": "2.00", "sort_order": 1},
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert Decimal(str(body["subtotal"])) == Decimal("50.01")
    assert Decimal(str(body["vat_amount"])) == Decimal("5.00")
    assert Decimal(str(body["total_amount"])) == Decimal("55.01")
    assert [item["sort_order"] for item in body["items"]] == [1, 2]


def test_create_estimate_validation_and_option_errors() -> None:
    inactive_option_id = create_option("Inactive", "100.00", active=False)
    active_option_id = create_option("Active", "100.00")

    assert client.post("/api/estimates", json={"customer_name": "Alice", "items": []}).status_code == 422
    assert client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": active_option_id, "quantity": "0"}]},
    ).status_code == 422
    assert client.post(
        "/api/estimates",
        json={
            "customer_name": "Alice",
            "items": [
                {"option_id": active_option_id, "quantity": "1"},
                {"option_id": active_option_id, "quantity": "2"},
            ],
        },
    ).status_code == 422
    assert client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": 999, "quantity": "1"}]},
    ).status_code == 404
    assert client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": inactive_option_id, "quantity": "1"}]},
    ).status_code == 409


def test_list_get_and_patch_estimate() -> None:
    option_id = create_option("Patch", "50.00")
    created = client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": option_id, "quantity": "1"}]},
    ).json()

    listed = client.get("/api/estimates", params={"customer_name": "ali", "status": "draft"})
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == created["id"]

    fetched = client.get(f"/api/estimates/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["items"][0]["option_name_snapshot"] == "Patch"

    patched = client.patch(
        f"/api/estimates/{created['id']}",
        json={"customer_name": "Alice Updated", "notes": "updated"},
    )
    assert patched.status_code == 200
    assert patched.json()["customer_name"] == "Alice Updated"
    assert patched.json()["status"] == "draft"
    assert patched.json()["notes"] == "updated"

    submitted = client.patch(f"/api/estimates/{created['id']}", json={"status": "submitted"})
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"

    assert client.patch(f"/api/estimates/{created['id']}", json={"status": "bad"}).status_code == 422
    assert client.get("/api/estimates/999").status_code == 404


def test_snapshot_does_not_change_when_option_price_changes() -> None:
    option_id = create_option("Snapshot", "100.00")
    created = client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": option_id, "quantity": "2"}]},
    ).json()

    with TestingSessionLocal() as db:
        option = db.get(Option, option_id)
        option.default_price = Decimal("999.00")
        db.commit()

    existing = client.get(f"/api/estimates/{created['id']}").json()
    assert Decimal(str(existing["items"][0]["unit_price_snapshot"])) == Decimal("100.00")
    assert Decimal(str(existing["items"][0]["line_total"])) == Decimal("200.00")
    assert Decimal(str(existing["subtotal"])) == Decimal("200.00")

    new_estimate = client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": option_id, "quantity": "1"}]},
    ).json()
    assert Decimal(str(new_estimate["items"][0]["unit_price_snapshot"])) == Decimal("999.00")


def test_create_estimate_rolls_back_on_failure(monkeypatch) -> None:
    option_id = create_option("Rollback", "100.00")

    monkeypatch.setattr(estimate_crud, "generate_estimate_number", lambda: "EST-DUPLICATE")
    first = client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": option_id, "quantity": "1"}]},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/estimates",
        json={"customer_name": "Bob", "items": [{"option_id": option_id, "quantity": "1"}]},
    )
    assert second.status_code == 409

    with TestingSessionLocal() as db:
        estimates = db.scalars(select(Estimate)).all()
        estimate_items = db.scalars(select(EstimateItem)).all()
        assert len(estimates) == 1
        assert len(estimate_items) == 1

def test_replace_items_preserves_existing_snapshot_and_recalculates_totals() -> None:
    option_a = create_option("Replace A", "100.00")
    option_b = create_option("Replace B", "50.00")
    created = client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": option_a, "quantity": "1.00"}]},
    ).json()

    with TestingSessionLocal() as db:
        option = db.get(Option, option_a)
        option.default_price = Decimal("999.00")
        db.commit()

    replaced = client.put(
        f"/api/estimates/{created['id']}/items",
        json={
            "items": [
                {"option_id": option_a, "quantity": "2.00", "sort_order": 2},
                {"option_id": option_b, "quantity": "3.00", "sort_order": 1},
            ]
        },
    )

    assert replaced.status_code == 200
    body = replaced.json()
    assert [item["option_id"] for item in body["items"]] == [option_b, option_a]
    existing = next(item for item in body["items"] if item["option_id"] == option_a)
    added = next(item for item in body["items"] if item["option_id"] == option_b)
    assert Decimal(str(existing["unit_price_snapshot"])) == Decimal("100.00")
    assert Decimal(str(existing["line_total"])) == Decimal("200.00")
    assert Decimal(str(added["unit_price_snapshot"])) == Decimal("50.00")
    assert Decimal(str(body["subtotal"])) == Decimal("350.00")
    assert Decimal(str(body["vat_amount"])) == Decimal("35.00")
    assert Decimal(str(body["total_amount"])) == Decimal("385.00")


def test_replace_items_removes_missing_items_and_uses_current_price_when_readded() -> None:
    option_a = create_option("Remove A", "100.00")
    option_b = create_option("Remove B", "50.00")
    created = client.post(
        "/api/estimates",
        json={
            "customer_name": "Alice",
            "items": [
                {"option_id": option_a, "quantity": "1.00"},
                {"option_id": option_b, "quantity": "1.00"},
            ],
        },
    ).json()

    removed = client.put(
        f"/api/estimates/{created['id']}/items",
        json={"items": [{"option_id": option_b, "quantity": "1.00"}]},
    ).json()
    assert [item["option_id"] for item in removed["items"]] == [option_b]

    with TestingSessionLocal() as db:
        option = db.get(Option, option_a)
        option.default_price = Decimal("200.00")
        db.commit()

    readded = client.put(
        f"/api/estimates/{created['id']}/items",
        json={
            "items": [
                {"option_id": option_b, "quantity": "1.00"},
                {"option_id": option_a, "quantity": "1.00"},
            ]
        },
    ).json()
    added_again = next(item for item in readded["items"] if item["option_id"] == option_a)
    assert Decimal(str(added_again["unit_price_snapshot"])) == Decimal("200.00")


def test_replace_items_validation_and_state_errors() -> None:
    option_id = create_option("Replace Errors", "100.00")
    inactive_option_id = create_option("Replace Inactive", "100.00", active=False)
    created = client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": option_id, "quantity": "1.00"}]},
    ).json()

    assert client.put(f"/api/estimates/{created['id']}/items", json={"items": []}).status_code == 422
    assert client.put(
        f"/api/estimates/{created['id']}/items",
        json={"items": [{"option_id": option_id, "quantity": "0"}]},
    ).status_code == 422
    assert client.put(
        f"/api/estimates/{created['id']}/items",
        json={"items": [{"option_id": option_id, "quantity": "1"}, {"option_id": option_id, "quantity": "2"}]},
    ).status_code == 422
    assert client.put(
        f"/api/estimates/{created['id']}/items",
        json={"items": [{"option_id": 999, "quantity": "1"}]},
    ).status_code == 404
    assert client.put(
        f"/api/estimates/{created['id']}/items",
        json={"items": [{"option_id": inactive_option_id, "quantity": "1"}]},
    ).status_code == 409
    assert client.put("/api/estimates/999/items", json={"items": [{"option_id": option_id, "quantity": "1"}]}).status_code == 404

    submitted = client.patch(f"/api/estimates/{created['id']}", json={"status": "submitted"})
    assert submitted.status_code == 200
    assert client.put(
        f"/api/estimates/{created['id']}/items",
        json={"items": [{"option_id": option_id, "quantity": "2"}]},
    ).status_code == 409


def test_status_transition_rules_and_patch_policy() -> None:
    option_id = create_option("Status", "100.00")
    created = client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": option_id, "quantity": "1.00"}]},
    ).json()
    estimate_id = created["id"]

    assert client.patch(f"/api/estimates/{estimate_id}", json={}).status_code == 422
    assert client.patch(
        f"/api/estimates/{estimate_id}", json={"status": "submitted", "notes": "mixed"}
    ).status_code == 422
    assert client.patch(f"/api/estimates/{estimate_id}", json={"status": "confirmed"}).status_code == 409
    assert client.patch(f"/api/estimates/{estimate_id}", json={"status": "draft"}).status_code == 200
    assert client.patch(f"/api/estimates/{estimate_id}", json={"status": "submitted"}).status_code == 200
    assert client.patch(f"/api/estimates/{estimate_id}", json={"customer_name": "Nope"}).status_code == 409
    assert client.patch(f"/api/estimates/{estimate_id}", json={"status": "draft"}).status_code == 200
    assert client.patch(f"/api/estimates/{estimate_id}", json={"status": "cancelled"}).status_code == 200
    assert client.patch(f"/api/estimates/{estimate_id}", json={"status": "cancelled"}).status_code == 200
    assert client.patch(f"/api/estimates/{estimate_id}", json={"status": "submitted"}).status_code == 409
    assert client.patch(f"/api/estimates/{estimate_id}", json={"notes": "Nope"}).status_code == 409


def test_submitted_and_confirmed_item_changes_are_rejected() -> None:
    option_id = create_option("Locked", "100.00")
    submitted = client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": option_id, "quantity": "1.00"}]},
    ).json()
    submitted_id = submitted["id"]
    assert client.patch(f"/api/estimates/{submitted_id}", json={"status": "submitted"}).status_code == 200
    assert client.put(
        f"/api/estimates/{submitted_id}/items",
        json={"items": [{"option_id": option_id, "quantity": "2.00"}]},
    ).status_code == 409

    confirmed = client.post(
        "/api/estimates",
        json={"customer_name": "Bob", "items": [{"option_id": option_id, "quantity": "1.00"}]},
    ).json()
    confirmed_id = confirmed["id"]
    assert client.patch(f"/api/estimates/{confirmed_id}", json={"status": "submitted"}).status_code == 200
    assert client.patch(f"/api/estimates/{confirmed_id}", json={"status": "confirmed"}).status_code == 200
    assert client.put(
        f"/api/estimates/{confirmed_id}/items",
        json={"items": [{"option_id": option_id, "quantity": "2.00"}]},
    ).status_code == 409
    assert client.patch(f"/api/estimates/{confirmed_id}", json={"status": "draft"}).status_code == 409


def test_replace_items_rolls_back_on_failure(monkeypatch) -> None:
    option_a = create_option("Rollback Replace A", "100.00")
    option_b = create_option("Rollback Replace B", "50.00")
    created = client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": option_a, "quantity": "1.00"}]},
    ).json()

    def broken_calculate_totals(*args, **kwargs):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("app.crud.estimate.calculate_totals", broken_calculate_totals)
    response = client.put(
        f"/api/estimates/{created['id']}/items",
        json={"items": [{"option_id": option_b, "quantity": "2.00"}]},
    )
    assert response.status_code == 500

    with TestingSessionLocal() as db:
        estimate = db.get(Estimate, created["id"])
        assert len(estimate.items) == 1
        assert estimate.items[0].option_id == option_a
        assert estimate.subtotal == Decimal("100.00")


def test_submit_recalculates_totals() -> None:
    option_id = create_option("Submit Recalc", "100.00")
    created = client.post(
        "/api/estimates",
        json={"customer_name": "Alice", "items": [{"option_id": option_id, "quantity": "2.00"}]},
    ).json()

    with TestingSessionLocal() as db:
        estimate = db.get(Estimate, created["id"])
        estimate.subtotal = Decimal("1.00")
        estimate.vat_amount = Decimal("1.00")
        estimate.total_amount = Decimal("1.00")
        db.commit()

    submitted = client.patch(f"/api/estimates/{created['id']}", json={"status": "submitted"})
    assert submitted.status_code == 200
    body = submitted.json()
    assert body["status"] == "submitted"
    assert Decimal(str(body["subtotal"])) == Decimal("200.00")
    assert Decimal(str(body["vat_amount"])) == Decimal("20.00")
    assert Decimal(str(body["total_amount"])) == Decimal("220.00")

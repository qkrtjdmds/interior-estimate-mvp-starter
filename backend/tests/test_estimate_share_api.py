import os
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.crud.admin_user import create_admin_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AdminUser, Category, Estimate, EstimateItem, EstimateShare, Item, Option

TEST_JWT_SECRET = "test-jwt-secret-with-at-least-32-characters"

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
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    settings.jwt_secret_key = TEST_JWT_SECRET
    settings.jwt_algorithm = "HS256"
    settings.jwt_access_token_expire_minutes = 480
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def create_admin_token() -> str:
    with TestingSessionLocal() as db:
        create_admin_user(db, "admin@example.com", "AdminPass123")
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "AdminPass123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_submitted_estimate(status: str = "submitted") -> int:
    suffix = uuid4().hex[:8]
    with TestingSessionLocal() as db:
        category = Category(name=f"Wall {suffix}")
        db.add(category)
        db.flush()
        item = Item(category_id=category.id, name=f"Wallpaper {suffix}")
        db.add(item)
        db.flush()
        option = Option(item_id=item.id, name=f"Silk {suffix}", description="Silk wallpaper", unit="평", default_price=Decimal("45000.00"))
        db.add(option)
        db.commit()
        option_id = option.id

    created = client.post(
        "/api/estimates",
        json={
            "customer_name": "박성민",
            "customer_phone": "010-0000-0000",
            "project_address": "Seoul",
            "notes": "private memo",
            "items": [{"option_id": option_id, "quantity": "2.00", "sort_order": 1}],
        },
    )
    assert created.status_code == 201
    estimate_id = created.json()["id"]
    with TestingSessionLocal() as db:
        estimate = db.get(Estimate, estimate_id)
        estimate.status = status
        db.commit()
    return estimate_id


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_share_token_create_stores_only_hash_and_public_lookup() -> None:
    admin_token = create_admin_token()
    estimate_id = create_submitted_estimate()

    response = client.post(
        f"/api/estimates/{estimate_id}/share",
        json={"expires_in_days": 30},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 201
    body = response.json()
    raw_token = body["share_token"]
    assert raw_token
    assert body["notice"] == "This token is shown only once."

    with TestingSessionLocal() as db:
        share = db.scalar(select(EstimateShare).where(EstimateShare.estimate_id == estimate_id))
        assert share is not None
        assert share.token_hash != raw_token
        assert len(share.token_hash) == 64
        assert raw_token not in share.token_hash

    public = client.get("/api/public/estimate", headers={"X-Estimate-Share-Token": raw_token})
    assert public.status_code == 200
    public_body = public.json()
    assert public_body["estimate_number"].startswith("EST-")
    assert public_body["status"] == "submitted"
    assert public_body["customer_name_masked"] == "박*민"
    assert public_body["items"][0]["option_name"].startswith("Silk")
    assert Decimal(str(public_body["items"][0]["unit_price"])) == Decimal("45000.00")
    assert "id" not in public_body
    assert "customer_phone" not in public_body
    assert "project_address" not in public_body
    assert "notes" not in public_body
    assert "option_id" not in public_body["items"][0]
    assert "token_hash" not in public_body
    assert public.headers["cache-control"] == "no-store"
    assert public.headers["pragma"] == "no-cache"
    assert public.headers["referrer-policy"] == "no-referrer"
    assert public.headers["x-content-type-options"] == "nosniff"


def test_share_reissue_revokes_previous_active_token() -> None:
    admin_token = create_admin_token()
    estimate_id = create_submitted_estimate()
    first = client.post(f"/api/estimates/{estimate_id}/share", headers=auth_headers(admin_token)).json()["share_token"]
    second_response = client.post(f"/api/estimates/{estimate_id}/share", headers=auth_headers(admin_token))

    assert second_response.status_code == 201
    second = second_response.json()["share_token"]
    assert second != first
    assert client.get("/api/public/estimate", headers={"X-Estimate-Share-Token": first}).status_code == 404
    assert client.get("/api/public/estimate", headers={"X-Estimate-Share-Token": second}).status_code == 200

    with TestingSessionLocal() as db:
        shares = db.scalars(select(EstimateShare).where(EstimateShare.estimate_id == estimate_id)).all()
        assert len(shares) == 2
        assert sum(1 for share in shares if share.active) == 1
        assert sum(1 for share in shares if share.revoked_at is not None) == 1


def test_share_status_hides_raw_token_and_hash() -> None:
    admin_token = create_admin_token()
    estimate_id = create_submitted_estimate()
    client.post(f"/api/estimates/{estimate_id}/share", headers=auth_headers(admin_token))

    status_response = client.get(f"/api/estimates/{estimate_id}/share", headers=auth_headers(admin_token))

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["active"] is True
    assert body["access_count"] == 0
    assert "share_token" not in body
    assert "token_hash" not in body


def test_revoke_share_is_idempotent() -> None:
    admin_token = create_admin_token()
    estimate_id = create_submitted_estimate()
    raw_token = client.post(f"/api/estimates/{estimate_id}/share", headers=auth_headers(admin_token)).json()["share_token"]

    first = client.delete(f"/api/estimates/{estimate_id}/share", headers=auth_headers(admin_token))
    second = client.delete(f"/api/estimates/{estimate_id}/share", headers=auth_headers(admin_token))

    assert first.status_code == 204
    assert second.status_code == 204
    assert client.get("/api/public/estimate", headers={"X-Estimate-Share-Token": raw_token}).status_code == 404


def test_share_admin_api_requires_auth_and_shareable_status() -> None:
    submitted_id = create_submitted_estimate()
    draft_id = create_submitted_estimate(status="draft")
    cancelled_id = create_submitted_estimate(status="cancelled")
    admin_token = create_admin_token()

    assert client.post(f"/api/estimates/{submitted_id}/share").status_code == 401
    assert client.get(f"/api/estimates/{submitted_id}/share").status_code == 401
    assert client.delete(f"/api/estimates/{submitted_id}/share").status_code == 401
    assert client.post(f"/api/estimates/{draft_id}/share", headers=auth_headers(admin_token)).status_code == 409
    assert client.post(f"/api/estimates/{cancelled_id}/share", headers=auth_headers(admin_token)).status_code == 409
    assert client.post("/api/estimates/999/share", headers=auth_headers(admin_token)).status_code == 404


def test_confirmed_share_success_and_validation() -> None:
    admin_token = create_admin_token()
    estimate_id = create_submitted_estimate(status="confirmed")

    assert client.post(f"/api/estimates/{estimate_id}/share", json={"expires_in_days": 0}, headers=auth_headers(admin_token)).status_code == 422
    assert client.post(f"/api/estimates/{estimate_id}/share", json={"expires_in_days": 91}, headers=auth_headers(admin_token)).status_code == 422
    assert client.post(f"/api/estimates/{estimate_id}/share", json={"expires_in_days": 1}, headers=auth_headers(admin_token)).status_code == 201


def test_public_lookup_errors_for_missing_invalid_expired_and_revoked_tokens() -> None:
    admin_token = create_admin_token()
    estimate_id = create_submitted_estimate()
    raw_token = client.post(f"/api/estimates/{estimate_id}/share", headers=auth_headers(admin_token)).json()["share_token"]

    assert client.get("/api/public/estimate").status_code == 401
    assert client.get("/api/public/estimate", headers={"X-Estimate-Share-Token": "invalid"}).status_code == 404

    with TestingSessionLocal() as db:
        share = db.scalar(select(EstimateShare).where(EstimateShare.estimate_id == estimate_id, EstimateShare.active.is_(True)))
        share.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
    assert client.get("/api/public/estimate", headers={"X-Estimate-Share-Token": raw_token}).status_code == 410

    new_token = client.post(f"/api/estimates/{estimate_id}/share", headers=auth_headers(admin_token)).json()["share_token"]
    client.delete(f"/api/estimates/{estimate_id}/share", headers=auth_headers(admin_token))
    assert client.get("/api/public/estimate", headers={"X-Estimate-Share-Token": new_token}).status_code == 404


def test_public_lookup_increments_access_count_and_does_not_create_estimates() -> None:
    admin_token = create_admin_token()
    estimate_id = create_submitted_estimate()
    raw_token = client.post(f"/api/estimates/{estimate_id}/share", headers=auth_headers(admin_token)).json()["share_token"]

    with TestingSessionLocal() as db:
        estimates_before = db.scalar(select(func.count()).select_from(Estimate))
        items_before = db.scalar(select(func.count()).select_from(EstimateItem))

    assert client.get("/api/public/estimate", headers={"X-Estimate-Share-Token": raw_token}).status_code == 200
    assert client.get("/api/public/estimate", headers={"X-Estimate-Share-Token": raw_token}).status_code == 200

    with TestingSessionLocal() as db:
        share = db.scalar(select(EstimateShare).where(EstimateShare.estimate_id == estimate_id, EstimateShare.active.is_(True)))
        assert share.access_count == 2
        assert share.last_accessed_at is not None
        assert db.scalar(select(func.count()).select_from(Estimate)) == estimates_before
        assert db.scalar(select(func.count()).select_from(EstimateItem)) == items_before


def test_cancelled_estimate_revokes_active_share() -> None:
    admin_token = create_admin_token()
    estimate_id = create_submitted_estimate()
    raw_token = client.post(f"/api/estimates/{estimate_id}/share", headers=auth_headers(admin_token)).json()["share_token"]

    cancelled = client.patch(f"/api/estimates/{estimate_id}", json={"status": "cancelled"}, headers=auth_headers(admin_token))

    assert cancelled.status_code == 200
    assert client.get("/api/public/estimate", headers={"X-Estimate-Share-Token": raw_token}).status_code == 404
    with TestingSessionLocal() as db:
        share = db.scalar(select(EstimateShare).where(EstimateShare.estimate_id == estimate_id))
        assert share.active is False
        assert share.revoked_at is not None



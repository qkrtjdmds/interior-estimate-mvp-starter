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
from app.services.estimate_pdf import format_money, format_quantity, sanitize_pdf_filename

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


def create_estimate(status: str = "submitted", item_count: int = 1) -> tuple[int, int]:
    suffix = uuid4().hex[:8]
    with TestingSessionLocal() as db:
        category = Category(name=f"Wall {suffix}")
        db.add(category)
        db.flush()
        item = Item(category_id=category.id, name=f"Wallpaper {suffix}")
        db.add(item)
        db.flush()
        option_ids = []
        for index in range(item_count):
            option = Option(
                item_id=item.id,
                name=f"Silk {suffix} {index}",
                description="Long description for wrapping " * 3,
                unit="평",
                default_price=Decimal("45000.00") + Decimal(index),
            )
            db.add(option)
            db.flush()
            option_ids.append(option.id)
        db.commit()

    payload_items = [{"option_id": option_id, "quantity": "2.00", "sort_order": index} for index, option_id in enumerate(option_ids)]
    created = client.post(
        "/api/estimates",
        json={
            "customer_name": "박성민",
            "customer_phone": "010-0000-0000",
            "project_address": "Seoul",
            "notes": "private memo",
            "items": payload_items,
        },
    )
    assert created.status_code == 201
    estimate_id = created.json()["id"]
    with TestingSessionLocal() as db:
        estimate = db.get(Estimate, estimate_id)
        estimate.status = status
        db.commit()
    return estimate_id, option_ids[0]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_share_token(estimate_id: int, admin_token: str) -> str:
    response = client.post(f"/api/estimates/{estimate_id}/share", headers=headers(admin_token))
    assert response.status_code == 201
    return response.json()["share_token"]


def assert_pdf_response(response) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    assert response.content.startswith(b"%PDF")


def test_admin_pdf_generation_for_all_statuses() -> None:
    admin_token = create_admin_token()
    for status in ["draft", "submitted", "confirmed", "cancelled"]:
        estimate_id, _ = create_estimate(status=status)
        response = client.get(f"/api/estimates/{estimate_id}/pdf", headers=headers(admin_token))
        assert_pdf_response(response)


def test_admin_pdf_requires_auth_and_missing_estimate_returns_404() -> None:
    admin_token = create_admin_token()
    assert client.get("/api/estimates/999/pdf", headers=headers(admin_token)).status_code == 404
    estimate_id, _ = create_estimate()
    assert client.get(f"/api/estimates/{estimate_id}/pdf").status_code == 401


def test_public_pdf_success_headers_and_access_count() -> None:
    admin_token = create_admin_token()
    estimate_id, _ = create_estimate(status="submitted")
    raw_token = create_share_token(estimate_id, admin_token)

    response = client.get("/api/public/estimate/pdf", headers={"X-Estimate-Share-Token": raw_token})

    assert_pdf_response(response)
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    with TestingSessionLocal() as db:
        share = db.scalar(select(EstimateShare).where(EstimateShare.estimate_id == estimate_id, EstimateShare.active.is_(True)))
        assert share.access_count == 1
        assert share.last_accessed_at is not None


def test_public_pdf_token_errors() -> None:
    admin_token = create_admin_token()
    estimate_id, _ = create_estimate(status="submitted")
    raw_token = create_share_token(estimate_id, admin_token)

    assert client.get("/api/public/estimate/pdf").status_code == 401
    assert client.get("/api/public/estimate/pdf", headers={"X-Estimate-Share-Token": "invalid"}).status_code == 404
    with TestingSessionLocal() as db:
        share = db.scalar(select(EstimateShare).where(EstimateShare.estimate_id == estimate_id, EstimateShare.active.is_(True)))
        share.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
    assert client.get("/api/public/estimate/pdf", headers={"X-Estimate-Share-Token": raw_token}).status_code == 410


def test_public_pdf_revoked_and_cancelled_are_blocked() -> None:
    admin_token = create_admin_token()
    estimate_id, _ = create_estimate(status="submitted")
    raw_token = create_share_token(estimate_id, admin_token)
    assert client.delete(f"/api/estimates/{estimate_id}/share", headers=headers(admin_token)).status_code == 204
    assert client.get("/api/public/estimate/pdf", headers={"X-Estimate-Share-Token": raw_token}).status_code == 404

    cancelled_id, _ = create_estimate(status="submitted")
    cancelled_token = create_share_token(cancelled_id, admin_token)
    assert client.patch(f"/api/estimates/{cancelled_id}", json={"status": "cancelled"}, headers=headers(admin_token)).status_code == 200
    assert client.get("/api/public/estimate/pdf", headers={"X-Estimate-Share-Token": cancelled_token}).status_code == 404


def test_pdf_generation_does_not_create_estimates_and_uses_snapshot_price() -> None:
    admin_token = create_admin_token()
    estimate_id, option_id = create_estimate(status="submitted")
    raw_token = create_share_token(estimate_id, admin_token)

    with TestingSessionLocal() as db:
        estimate_count = db.scalar(select(func.count()).select_from(Estimate))
        item_count = db.scalar(select(func.count()).select_from(EstimateItem))
        option = db.get(Option, option_id)
        option.default_price = Decimal("999999.00")
        db.commit()

    admin_pdf = client.get(f"/api/estimates/{estimate_id}/pdf", headers=headers(admin_token))
    public_pdf = client.get("/api/public/estimate/pdf", headers={"X-Estimate-Share-Token": raw_token})

    assert_pdf_response(admin_pdf)
    assert_pdf_response(public_pdf)
    with TestingSessionLocal() as db:
        estimate = db.get(Estimate, estimate_id)
        assert estimate.items[0].unit_price_snapshot == Decimal("45000.00")
        assert db.scalar(select(func.count()).select_from(Estimate)) == estimate_count
        assert db.scalar(select(func.count()).select_from(EstimateItem)) == item_count


def test_multi_page_pdf_generation() -> None:
    admin_token = create_admin_token()
    estimate_id, _ = create_estimate(status="submitted", item_count=55)
    response = client.get(f"/api/estimates/{estimate_id}/pdf", headers=headers(admin_token))
    assert_pdf_response(response)
    assert response.content.count(b"/Type /Page") >= 2


def test_pdf_font_error_is_handled(monkeypatch) -> None:
    import app.api.estimates as estimate_api

    def raise_font_error(*args, **kwargs):
        from app.services.estimate_pdf import PdfFontConfigurationError

        raise PdfFontConfigurationError("missing")

    admin_token = create_admin_token()
    estimate_id, _ = create_estimate(status="submitted")
    monkeypatch.setattr(estimate_api, "build_estimate_pdf", raise_font_error)

    response = client.get(f"/api/estimates/{estimate_id}/pdf", headers=headers(admin_token))
    assert response.status_code == 503


def test_public_and_admin_data_policy_for_pdf(monkeypatch) -> None:
    import app.api.estimate_shares as share_api
    import app.api.estimates as estimate_api

    captured = []

    def fake_build(estimate, options):
        captured.append(
            {
                "public": options.public,
                "customer_name": estimate.customer_name,
                "customer_phone": estimate.customer_phone if not options.public else None,
                "project_address": estimate.project_address if not options.public else None,
                "notes": estimate.notes if not options.public else None,
            }
        )
        return b"%PDF-1.4\n%fake"

    admin_token = create_admin_token()
    estimate_id, _ = create_estimate(status="submitted")
    raw_token = create_share_token(estimate_id, admin_token)
    monkeypatch.setattr(estimate_api, "build_estimate_pdf", fake_build)
    monkeypatch.setattr(share_api, "build_estimate_pdf", fake_build)

    assert client.get(f"/api/estimates/{estimate_id}/pdf", headers=headers(admin_token)).status_code == 200
    assert client.get("/api/public/estimate/pdf", headers={"X-Estimate-Share-Token": raw_token}).status_code == 200
    assert captured[0]["public"] is False
    assert captured[0]["customer_phone"] == "010-0000-0000"
    assert captured[0]["project_address"] == "Seoul"
    assert captured[0]["notes"] == "private memo"
    assert captured[1]["public"] is True
    assert captured[1]["customer_phone"] is None
    assert captured[1]["project_address"] is None
    assert captured[1]["notes"] is None


def test_format_helpers_and_safe_filename() -> None:
    assert format_money(Decimal("45000.00")) == "45,000원"
    assert format_quantity(Decimal("2.50")) == "2.5"
    assert sanitize_pdf_filename("EST-20260903-ABC\r\n.pdf") == "estimate_EST-20260903-ABC_.pdf.pdf"

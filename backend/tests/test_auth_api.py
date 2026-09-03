import os
from collections.abc import Generator
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password, validate_password_policy, verify_password
from app.crud.admin_user import create_admin_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AdminUser, Category, Estimate, EstimateItem, Item, Option  # noqa: F401

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


def test_password_hash_does_not_include_plaintext_and_verify() -> None:
    password = "AdminPass123"
    password_hash = hash_password(password)

    assert password not in password_hash
    assert verify_password(password, password_hash) is True
    assert verify_password("WrongPass123", password_hash) is False


def test_password_policy() -> None:
    validate_password_policy("StrongPass123")
    with pytest.raises(ValueError):
        validate_password_policy("short1")
    with pytest.raises(ValueError):
        validate_password_policy("OnlyLettersHere")
    with pytest.raises(ValueError):
        validate_password_policy("1234567890")
    with pytest.raises(ValueError):
        validate_password_policy("password123")


def test_login_success_and_me_hides_password_hash() -> None:
    with TestingSessionLocal() as db:
        admin = create_admin_user(db, " Admin@Example.COM ", "AdminPass123")
        assert admin.email == "admin@example.com"
        assert admin.last_login_at is None

    login = client.post("/api/auth/login", json={"email": "ADMIN@example.com", "password": "AdminPass123"})
    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 28800
    assert body["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["email"] == "admin@example.com"
    assert "password_hash" not in me_body
    assert me_body["last_login_at"] is not None


def test_login_failures_return_401() -> None:
    with TestingSessionLocal() as db:
        create_admin_user(db, "admin@example.com", "AdminPass123")

    wrong_password = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "WrongPass123"})
    missing_user = client.post("/api/auth/login", json={"email": "missing@example.com", "password": "AdminPass123"})

    assert wrong_password.status_code == 401
    assert missing_user.status_code == 401
    assert wrong_password.json() == missing_user.json()


def test_inactive_admin_login_is_blocked() -> None:
    with TestingSessionLocal() as db:
        admin = create_admin_user(db, "admin@example.com", "AdminPass123")
        admin.active = False
        db.commit()

    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "AdminPass123"})
    assert response.status_code == 401


def test_me_token_errors_and_inactive_admin() -> None:
    with TestingSessionLocal() as db:
        admin = create_admin_user(db, "admin@example.com", "AdminPass123")
        admin_id = admin.id

    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer bad-token"}).status_code == 401

    expired = jwt.encode(
        {"sub": str(admin_id), "type": "access", "iat": 1, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    wrong_type = jwt.encode(
        {"sub": str(admin_id), "type": "refresh", "iat": 1, "exp": datetime.now(timezone.utc) + timedelta(minutes=1)},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    missing_admin = jwt.encode(
        {"sub": "999", "type": "access", "iat": 1, "exp": datetime.now(timezone.utc) + timedelta(minutes=1)},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )

    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {wrong_type}"}).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {missing_admin}"}).status_code == 401

    valid = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "AdminPass123"}).json()["access_token"]
    with TestingSessionLocal() as db:
        admin = db.get(AdminUser, admin_id)
        admin.active = False
        db.commit()
    inactive = client.get("/api/auth/me", headers={"Authorization": f"Bearer {valid}"})
    assert inactive.status_code == 403


def test_public_endpoints_do_not_require_auth() -> None:
    with TestingSessionLocal() as db:
        category = Category(name="Wall")
        db.add(category)
        db.flush()
        item = Item(category_id=category.id, name="Wallpaper")
        db.add(item)
        db.flush()
        option = Option(item_id=item.id, name="Silk", unit="평", default_price="45000")
        db.add(option)
        db.commit()
        option_id = option.id

    assert client.get("/").status_code == 200
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/health/db").status_code == 200
    assert client.get("/api/catalog").status_code == 200
    assert client.post("/api/estimates/preview", json={"items": [{"option_id": option_id, "quantity": "1"}]}).status_code == 200
    assert client.post("/api/estimates", json={"customer_name": "Alice", "items": [{"option_id": option_id, "quantity": "1"}]}).status_code == 201


def test_admin_endpoints_require_auth_and_accept_valid_token() -> None:
    with TestingSessionLocal() as db:
        create_admin_user(db, "admin@example.com", "AdminPass123")

    protected_requests = [
        ("get", "/api/categories", None),
        ("post", "/api/categories", {"name": "Paint"}),
        ("get", "/api/items", None),
        ("get", "/api/options", None),
        ("get", "/api/estimates", None),
    ]
    for method, path, payload in protected_requests:
        response = getattr(client, method)(path, json=payload) if payload is not None else getattr(client, method)(path)
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"

    token = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "AdminPass123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/categories", json={"name": "Paint"}, headers=headers)
    assert created.status_code == 201
    assert client.get("/api/categories", headers=headers).status_code == 200
    assert client.get("/api/estimates", headers=headers).status_code == 200

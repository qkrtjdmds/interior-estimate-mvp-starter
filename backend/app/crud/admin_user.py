from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, normalize_email, verify_password
from app.models import AdminUser


def get_admin_user(db: Session, admin_user_id: int) -> AdminUser | None:
    return db.get(AdminUser, admin_user_id)


def get_admin_user_by_email(db: Session, email: str) -> AdminUser | None:
    normalized = normalize_email(email)
    return db.scalar(select(AdminUser).where(func.lower(func.trim(AdminUser.email)) == normalized))


def create_admin_user(db: Session, email: str, password: str) -> AdminUser:
    admin_user = AdminUser(email=normalize_email(email), password_hash=hash_password(password), active=True)
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    return admin_user


def authenticate_admin_user(db: Session, email: str, password: str) -> AdminUser | None:
    admin_user = get_admin_user_by_email(db, email)
    if admin_user is None:
        return None
    if not verify_password(password, admin_user.password_hash):
        return None
    return admin_user


def mark_last_login(db: Session, admin_user: AdminUser) -> AdminUser:
    admin_user.last_login_at = datetime.now(timezone.utc)
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    return admin_user


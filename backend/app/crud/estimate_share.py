from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.models import Estimate, EstimateShare

SHAREABLE_STATUSES = {"submitted", "confirmed"}
PUBLIC_READABLE_STATUSES = {"submitted", "confirmed"}


def generate_share_token() -> str:
    return secrets.token_urlsafe(32)


def hash_share_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_active_share_for_estimate(db: Session, estimate_id: int) -> EstimateShare | None:
    return db.scalar(
        select(EstimateShare)
        .where(EstimateShare.estimate_id == estimate_id, EstimateShare.active.is_(True))
        .order_by(EstimateShare.created_at.desc(), EstimateShare.id.desc())
        .limit(1)
    )


def get_share_by_token(db: Session, raw_token: str) -> EstimateShare | None:
    token_hash = hash_share_token(raw_token)
    return db.scalar(
        select(EstimateShare)
        .options(selectinload(EstimateShare.estimate).selectinload(Estimate.items))
        .where(EstimateShare.token_hash == token_hash)
        .limit(1)
    )


def revoke_active_shares_for_estimate(db: Session, estimate_id: int, revoked_at: datetime | None = None) -> int:
    now = revoked_at or datetime.now(timezone.utc)
    result = db.execute(
        update(EstimateShare)
        .where(EstimateShare.estimate_id == estimate_id, EstimateShare.active.is_(True))
        .values(active=False, revoked_at=now)
    )
    return int(result.rowcount or 0)


def create_share(db: Session, estimate: Estimate, expires_in_days: int) -> tuple[EstimateShare, str]:
    now = datetime.now(timezone.utc)
    revoke_active_shares_for_estimate(db, estimate.id, now)

    raw_token = generate_share_token()
    share = EstimateShare(
        estimate_id=estimate.id,
        token_hash=hash_share_token(raw_token),
        active=True,
        expires_at=now + timedelta(days=expires_in_days),
        access_count=0,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share, raw_token


def revoke_share(db: Session, share: EstimateShare) -> EstimateShare:
    if share.active:
        share.active = False
        share.revoked_at = datetime.now(timezone.utc)
        db.add(share)
        db.commit()
        db.refresh(share)
    return share


def record_share_access(db: Session, share: EstimateShare) -> EstimateShare:
    share.access_count += 1
    share.last_accessed_at = datetime.now(timezone.utc)
    db.add(share)
    db.commit()
    db.refresh(share)
    return share


def mask_customer_name(name: str) -> str:
    stripped = name.strip()
    if not stripped:
        return ""
    if len(stripped) == 1:
        return "*"
    if len(stripped) == 2:
        return stripped[0] + "*"
    return stripped[0] + "*" * (len(stripped) - 2) + stripped[-1]

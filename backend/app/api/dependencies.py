from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import ExpiredTokenError, TokenError, decode_access_token
from app.crud.admin_user import get_admin_user
from app.db.session import get_db
from app.models import AdminUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_admin(db: DbSession, token: Annotated[str | None, Depends(oauth2_scheme)]) -> AdminUser:
    if not token:
        raise _credentials_error()
    try:
        payload = decode_access_token(token)
        admin_user_id = int(payload["sub"])
    except (ExpiredTokenError, TokenError, TypeError, ValueError):
        raise _credentials_error() from None

    admin_user = get_admin_user(db, admin_user_id)
    if admin_user is None:
        raise _credentials_error()
    if not admin_user.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive admin user")
    return admin_user

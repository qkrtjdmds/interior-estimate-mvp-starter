from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin
from app.core.security import create_access_token
from app.crud import admin_user as admin_user_crud
from app.db.session import get_db
from app.models import AdminUser
from app.schemas.auth import AdminUserResponse, LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[AdminUser, Depends(get_current_admin)]


def _invalid_login() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/login", response_model=TokenResponse, summary="Admin login")
def login(login_in: LoginRequest, db: DbSession) -> TokenResponse:
    admin_user = admin_user_crud.authenticate_admin_user(db, login_in.email, login_in.password)
    if admin_user is None or not admin_user.active:
        raise _invalid_login()
    try:
        admin_user_crud.mark_last_login(db, admin_user)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed") from exc
    access_token, expires_in = create_access_token(admin_user.id)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.get("/me", response_model=AdminUserResponse, summary="Get current admin")
def read_current_admin(current_admin: CurrentAdmin) -> AdminUserResponse:
    return current_admin

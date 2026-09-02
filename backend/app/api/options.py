from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.crud import option as option_crud
from app.db.session import get_db
from app.schemas.option import OptionCreate, OptionResponse, OptionUpdate

router = APIRouter(prefix="/api/options", tags=["options"])
DbSession = Annotated[Session, Depends(get_db)]


def _handle_db_error(db: Session, exc: SQLAlchemyError) -> None:
    db.rollback()
    if isinstance(exc, IntegrityError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Database constraint violation",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database operation failed",
    ) from exc


@router.post("", response_model=OptionResponse, status_code=status.HTTP_201_CREATED, summary="Create option")
def create_option(option_in: OptionCreate, db: DbSession) -> OptionResponse:
    if not option_crud.item_exists(db, option_in.item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    try:
        return option_crud.create_option(db, option_in)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)


@router.get("", response_model=list[OptionResponse], summary="List options")
def list_options(
    db: DbSession,
    item_id: int | None = None,
    active: bool | None = None,
    customer_visible: bool | None = None,
    recommended: bool | None = None,
    unit: str | None = None,
    name: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[OptionResponse]:
    return option_crud.get_options(
        db,
        item_id=item_id,
        active=active,
        customer_visible=customer_visible,
        recommended=recommended,
        unit=unit,
        name=name,
        skip=skip,
        limit=limit,
    )


@router.get("/{option_id}", response_model=OptionResponse, summary="Get option")
def get_option(option_id: int, db: DbSession) -> OptionResponse:
    option = option_crud.get_option(db, option_id)
    if option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")
    return option


@router.patch("/{option_id}", response_model=OptionResponse, summary="Update option")
def update_option(option_id: int, option_in: OptionUpdate, db: DbSession) -> OptionResponse:
    option = option_crud.get_option(db, option_id)
    if option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")
    if option_in.item_id is not None and not option_crud.item_exists(db, option_in.item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    try:
        return option_crud.update_option(db, option, option_in)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)


@router.delete("/{option_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete option")
def delete_option(option_id: int, db: DbSession) -> Response:
    option = option_crud.get_option(db, option_id)
    if option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")
    try:
        option_crud.delete_option(db, option)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
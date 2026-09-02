from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.crud import item as item_crud
from app.db.session import get_db
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate

router = APIRouter(prefix="/api/items", tags=["items"])
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


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED, summary="Create item")
def create_item(item_in: ItemCreate, db: DbSession) -> ItemResponse:
    if not item_crud.category_exists(db, item_in.category_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    try:
        return item_crud.create_item(db, item_in)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)


@router.get("", response_model=list[ItemResponse], summary="List items")
def list_items(
    db: DbSession,
    category_id: int | None = None,
    active: bool | None = None,
    customer_visible: bool | None = None,
    name: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[ItemResponse]:
    return item_crud.get_items(
        db,
        category_id=category_id,
        active=active,
        customer_visible=customer_visible,
        name=name,
        skip=skip,
        limit=limit,
    )


@router.get("/{item_id}", response_model=ItemResponse, summary="Get item")
def get_item(item_id: int, db: DbSession) -> ItemResponse:
    item = item_crud.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.patch("/{item_id}", response_model=ItemResponse, summary="Update item")
def update_item(item_id: int, item_in: ItemUpdate, db: DbSession) -> ItemResponse:
    item = item_crud.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item_in.category_id is not None and not item_crud.category_exists(db, item_in.category_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    try:
        return item_crud.update_item(db, item, item_in)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete item")
def delete_item(item_id: int, db: DbSession) -> Response:
    item = item_crud.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item_crud.item_has_options(db, item_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item has options and cannot be deleted",
        )
    try:
        item_crud.delete_item(db, item)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
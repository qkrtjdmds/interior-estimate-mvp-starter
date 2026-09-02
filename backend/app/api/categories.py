from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.crud import category as category_crud
from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter(prefix="/api/categories", tags=["categories"])
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


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, summary="Create category")
def create_category(category_in: CategoryCreate, db: DbSession) -> CategoryResponse:
    try:
        return category_crud.create_category(db, category_in)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)


@router.get("", response_model=list[CategoryResponse], summary="List categories")
def list_categories(
    db: DbSession,
    active: bool | None = None,
    customer_visible: bool | None = None,
    name: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[CategoryResponse]:
    return category_crud.get_categories(
        db,
        active=active,
        customer_visible=customer_visible,
        name=name,
        skip=skip,
        limit=limit,
    )


@router.get("/{category_id}", response_model=CategoryResponse, summary="Get category")
def get_category(category_id: int, db: DbSession) -> CategoryResponse:
    category = category_crud.get_category(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


@router.patch("/{category_id}", response_model=CategoryResponse, summary="Update category")
def update_category(category_id: int, category_in: CategoryUpdate, db: DbSession) -> CategoryResponse:
    category = category_crud.get_category(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    try:
        return category_crud.update_category(db, category, category_in)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete category")
def delete_category(category_id: int, db: DbSession) -> Response:
    category = category_crud.get_category(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if category_crud.category_has_items(db, category_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category has items and cannot be deleted",
        )
    try:
        category_crud.delete_category(db, category)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
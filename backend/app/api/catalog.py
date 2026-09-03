from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud.catalog import get_customer_catalog
from app.db.session import get_db
from app.schemas.catalog import CatalogCategoryResponse

router = APIRouter(prefix="/api/catalog", tags=["catalog"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[CatalogCategoryResponse], summary="Get customer catalog")
def get_catalog(db: DbSession) -> list[CatalogCategoryResponse]:
    return get_customer_catalog(db)
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CatalogOptionResponse(BaseModel):
    id: int
    name: str
    description: str | None
    unit: str
    default_price: Decimal
    recommended: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class CatalogItemResponse(BaseModel):
    id: int
    name: str
    description: str | None
    sort_order: int
    options: list[CatalogOptionResponse]

    model_config = ConfigDict(from_attributes=True)


class CatalogCategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None
    sort_order: int
    items: list[CatalogItemResponse]

    model_config = ConfigDict(from_attributes=True)
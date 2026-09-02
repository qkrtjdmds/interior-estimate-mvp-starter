from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OptionBase(BaseModel):
    item_id: int
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    unit: str = Field(min_length=1, max_length=20)
    default_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    recommended: bool = False
    active: bool = True
    customer_visible: bool = True
    sort_order: int = Field(default=0, ge=0)

    @field_validator("name", "unit")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class OptionCreate(OptionBase):
    pass


class OptionUpdate(BaseModel):
    item_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    default_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    recommended: bool | None = None
    active: bool | None = None
    customer_visible: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)

    @field_validator("name", "unit")
    @classmethod
    def text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("value must not be blank")
        return value


class OptionResponse(OptionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
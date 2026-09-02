from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ALLOWED_ESTIMATE_STATUSES = {"draft", "submitted", "confirmed", "cancelled"}


class EstimateItemCreate(BaseModel):
    option_id: int
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    sort_order: int = Field(default=0, ge=0)


class EstimateItemsReplace(BaseModel):
    items: list[EstimateItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def option_ids_must_be_unique(self) -> "EstimateItemsReplace":
        option_ids = [item.option_id for item in self.items]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("duplicate option_id is not allowed")
        return self


class EstimateItemResponse(BaseModel):
    id: int
    estimate_id: int
    option_id: int | None
    category_name_snapshot: str
    item_name_snapshot: str
    option_name_snapshot: str
    description_snapshot: str | None
    unit_snapshot: str
    unit_price_snapshot: Decimal
    quantity: Decimal
    line_total: Decimal
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EstimateCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=100)
    customer_phone: str | None = Field(default=None, max_length=50)
    project_address: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    valid_until: date | None = None
    items: list[EstimateItemCreate] = Field(min_length=1)

    @field_validator("customer_name")
    @classmethod
    def customer_name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("customer_name must not be blank")
        return value

    @model_validator(mode="after")
    def option_ids_must_be_unique(self) -> "EstimateCreate":
        option_ids = [item.option_id for item in self.items]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("duplicate option_id is not allowed")
        return self


class EstimateUpdate(BaseModel):
    customer_name: str | None = Field(default=None, min_length=1, max_length=100)
    customer_phone: str | None = Field(default=None, max_length=50)
    project_address: str | None = Field(default=None, max_length=255)
    status: str | None = None
    notes: str | None = None
    valid_until: date | None = None

    @field_validator("customer_name")
    @classmethod
    def customer_name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("customer_name must not be blank")
        return value

    @field_validator("status")
    @classmethod
    def status_must_be_allowed(cls, value: str | None) -> str | None:
        if value is not None and value not in ALLOWED_ESTIMATE_STATUSES:
            raise ValueError("invalid estimate status")
        return value


class EstimateListResponse(BaseModel):
    id: int
    estimate_number: str
    customer_name: str
    customer_phone: str | None
    project_address: str | None
    status: str
    subtotal: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    valid_until: date | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EstimateDetailResponse(EstimateListResponse):
    notes: str | None
    items: list[EstimateItemResponse]
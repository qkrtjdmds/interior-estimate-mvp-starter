from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class EstimateShareCreate(BaseModel):
    expires_in_days: int = Field(default=30, ge=1, le=90)


class EstimateShareCreateResponse(BaseModel):
    share_token: str
    expires_at: datetime
    created_at: datetime
    notice: str = "This token is shown only once."


class EstimateShareStatusResponse(BaseModel):
    active: bool
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    last_accessed_at: datetime | None
    access_count: int


class PublicEstimateItemResponse(BaseModel):
    category_name: str
    item_name: str
    option_name: str
    description: str | None
    unit: str
    unit_price: Decimal
    quantity: Decimal
    line_total: Decimal
    sort_order: int


class PublicEstimateResponse(BaseModel):
    estimate_number: str
    status: str
    customer_name_masked: str
    created_at: datetime
    valid_until: date | None
    items: list[PublicEstimateItemResponse]
    subtotal: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    total_amount: Decimal


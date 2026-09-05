from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin
from app.crud import estimate as estimate_crud
from app.crud import estimate_share as share_crud
from app.db.session import get_db
from app.models import Option
from app.schemas.estimate import (
    ALLOWED_ESTIMATE_STATUSES,
    EstimateAdminConsultationUpdate,
    EstimateCreate,
    EstimateDetailResponse,
    EstimateItemsReplace,
    EstimateListResponse,
    EstimatePreviewItemResponse,
    EstimatePreviewResponse,
    EstimateUpdate,
)
from app.services.estimate_calculator import DEFAULT_VAT_RATE, calculate_line_total, calculate_totals
from app.services.estimate_pdf import PdfFontConfigurationError, PdfGenerationError, PdfRenderOptions, build_estimate_pdf, sanitize_pdf_filename

router = APIRouter(prefix="/api/estimates", tags=["estimates"])
DbSession = Annotated[Session, Depends(get_db)]

ALLOWED_STATUS_TRANSITIONS = {
    "draft": {"draft", "submitted", "cancelled"},
    "submitted": {"submitted", "draft", "confirmed", "cancelled"},
    "confirmed": {"confirmed", "completed", "cancelled"},
    "completed": {"completed", "cancelled"},
    "cancelled": {"cancelled"},
}
BASIC_UPDATE_FIELDS = {"customer_name", "customer_phone", "customer_email", "housing_type", "floor_area_pyeong", "renovation_scope", "preferred_timeline", "project_address", "notes", "valid_until"}


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_stale_update(current_updated_at: datetime, expected_updated_at: datetime) -> bool:
    return abs((_normalize_datetime(current_updated_at) - _normalize_datetime(expected_updated_at)).total_seconds()) > 0.001


def _option_is_admin_usable(option: Option) -> bool:
    return option.active and option.item.active and option.item.category.active

def _handle_unexpected_error(db: Session, exc: Exception) -> None:
    db.rollback()
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed") from exc


def _handle_db_error(db: Session, exc: SQLAlchemyError) -> None:
    db.rollback()
    if isinstance(exc, IntegrityError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Database constraint violation") from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed") from exc


def _validate_status_filter(status_value: str | None) -> None:
    if status_value is not None and status_value not in ALLOWED_ESTIMATE_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid estimate status")


def _validate_status_transition(current_status: str, target_status: str) -> None:
    if target_status not in ALLOWED_STATUS_TRANSITIONS[current_status]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid estimate status transition")


def _validate_patch_policy(estimate_status: str, estimate_in: EstimateUpdate) -> None:
    changed_fields = set(estimate_in.model_dump(exclude_unset=True).keys())
    if not changed_fields:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="PATCH body must not be empty")

    has_status = "status" in changed_fields
    has_basic_fields = bool(changed_fields & BASIC_UPDATE_FIELDS)
    if has_status and has_basic_fields:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="status cannot be patched with other fields")

    if has_status:
        target_status = estimate_in.status
        if target_status is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="status must not be null")
        _validate_status_transition(estimate_status, target_status)
        return

    if estimate_status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only draft estimates can be edited")


def _validate_submit_ready(estimate) -> None:
    if not estimate.customer_name.strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="customer_name is required before submit")
    if not estimate.items:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="At least one estimate item is required")
    estimate_crud.recalculate_estimate_totals(estimate)


def _option_is_customer_usable(option: Option) -> bool:
    return (
        option.active
        and option.customer_visible
        and option.item.active
        and option.item.customer_visible
        and option.item.category.active
        and option.item.category.customer_visible
    )


def _load_options_or_raise(db: Session, item_requests, existing_option_ids: set[int] | None = None) -> dict[int, Option]:
    existing_option_ids = existing_option_ids or set()
    option_ids = [item.option_id for item in item_requests]
    options = estimate_crud.get_options_for_estimate(db, option_ids)
    options_by_id = {option.id: option for option in options}

    if any(option_id not in options_by_id for option_id in option_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")

    for option_id in option_ids:
        if option_id in existing_option_ids:
            continue
        if not _option_is_customer_usable(options_by_id[option_id]):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Option cannot be used")
    return options_by_id


def _build_preview(items_in: EstimateItemsReplace, options_by_id: dict[int, Option]) -> EstimatePreviewResponse:
    preview_items: list[EstimatePreviewItemResponse] = []
    line_totals: list[Decimal] = []
    for item_in in items_in.items:
        option = options_by_id[item_in.option_id]
        line_total = calculate_line_total(option.default_price, item_in.quantity)
        line_totals.append(line_total)
        preview_items.append(
            EstimatePreviewItemResponse(
                option_id=option.id,
                category_name=option.item.category.name,
                item_name=option.item.name,
                option_name=option.name,
                unit=option.unit,
                unit_price=option.default_price,
                quantity=item_in.quantity,
                line_total=line_total,
                sort_order=item_in.sort_order,
            )
        )
    preview_items.sort(key=lambda item: (item.sort_order, item.option_id))
    subtotal, vat_amount, total_amount = calculate_totals(line_totals, DEFAULT_VAT_RATE)
    return EstimatePreviewResponse(items=preview_items, subtotal=subtotal, vat_rate=DEFAULT_VAT_RATE, vat_amount=vat_amount, total_amount=total_amount)


@router.post(
    "",
    response_model=EstimateDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create estimate",
    responses={404: {"description": "Option not found"}, 409: {"description": "Option cannot be used or DB conflict"}},
)
def create_estimate(estimate_in: EstimateCreate, db: DbSession) -> EstimateDetailResponse:
    options_by_id = _load_options_or_raise(db, estimate_in.items)
    try:
        return estimate_crud.create_estimate(db, estimate_in, options_by_id)
    except estimate_crud.EstimateNumberGenerationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not generate unique estimate number") from exc
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)
    except Exception as exc:
        _handle_unexpected_error(db, exc)


@router.post(
    "/preview",
    response_model=EstimatePreviewResponse,
    summary="Preview estimate totals without saving",
    responses={404: {"description": "Option not found"}, 409: {"description": "Option cannot be used"}},
)
def preview_estimate(
    db: DbSession,
    items_in: EstimateItemsReplace = Body(
        openapi_examples={
            "basic": {
                "summary": "Preview estimate",
                "value": {"items": [{"option_id": 1, "quantity": "2.00", "sort_order": 1}]},
            }
        }
    ),
) -> EstimatePreviewResponse:
    options_by_id = _load_options_or_raise(db, items_in.items)
    return _build_preview(items_in, options_by_id)


@router.get("", response_model=list[EstimateListResponse], summary="List estimates", dependencies=[Depends(get_current_admin)])
def list_estimates(
    db: DbSession,
    status: str | None = None,
    customer_name: str | None = None,
    estimate_number: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[EstimateListResponse]:
    _validate_status_filter(status)
    return estimate_crud.get_estimates(db, status=status, customer_name=customer_name, estimate_number=estimate_number, created_from=created_from, created_to=created_to, skip=skip, limit=limit)


@router.get("/{estimate_id}", response_model=EstimateDetailResponse, summary="Get estimate", dependencies=[Depends(get_current_admin)])
def get_estimate(estimate_id: int, db: DbSession) -> EstimateDetailResponse:
    estimate = estimate_crud.get_estimate(db, estimate_id)
    if estimate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estimate not found")
    return estimate




@router.get(
    "/{estimate_id}/pdf",
    summary="Download estimate PDF",
    dependencies=[Depends(get_current_admin)],
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF file"},
        404: {"description": "Estimate not found"},
        503: {"description": "PDF font is not configured"},
    },
)
def download_estimate_pdf(estimate_id: int, db: DbSession) -> Response:
    estimate = estimate_crud.get_estimate(db, estimate_id)
    if estimate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estimate not found")
    try:
        pdf_bytes = build_estimate_pdf(estimate, PdfRenderOptions(public=False))
    except PdfFontConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="PDF font is not configured") from exc
    except PdfGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PDF generation failed") from exc

    filename = sanitize_pdf_filename(estimate.estimate_number)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )

@router.patch(
    "/{estimate_id}",
    response_model=EstimateDetailResponse,
    summary="Update estimate",
    dependencies=[Depends(get_current_admin)],
    responses={404: {"description": "Estimate not found"}, 409: {"description": "Invalid status transition or edit policy"}},
)
def update_estimate(estimate_id: int, estimate_in: EstimateUpdate, db: DbSession) -> EstimateDetailResponse:
    estimate = estimate_crud.get_estimate(db, estimate_id)
    if estimate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estimate not found")
    _validate_patch_policy(estimate.status, estimate_in)
    if estimate_in.status == "submitted":
        _validate_submit_ready(estimate)
    try:
        updated = estimate_crud.update_estimate(db, estimate, estimate_in)
        if estimate_in.status == "cancelled":
            share_crud.revoke_active_shares_for_estimate(db, updated.id)
            db.commit()
            updated = estimate_crud.get_estimate(db, updated.id) or updated
        return updated
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)
    except Exception as exc:
        _handle_unexpected_error(db, exc)


@router.put(
    "/{estimate_id}/consultation",
    response_model=EstimateDetailResponse,
    summary="Update estimate during admin consultation",
    dependencies=[Depends(get_current_admin)],
    responses={
        404: {"description": "Estimate or option not found"},
        409: {"description": "Estimate is not editable, stale update, or option cannot be used"},
    },
)
def update_estimate_consultation(estimate_id: int, estimate_in: EstimateAdminConsultationUpdate, db: DbSession) -> EstimateDetailResponse:
    estimate = estimate_crud.get_estimate(db, estimate_id)
    if estimate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estimate not found")
    if estimate.status != "submitted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only submitted estimates can be edited during consultation")
    if _is_stale_update(estimate.updated_at, estimate_in.expected_updated_at):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Estimate was changed by another request. Refresh and try again")

    option_ids = [item.option_id for item in estimate_in.items]
    options = estimate_crud.get_options_for_estimate(db, option_ids)
    options_by_id = {option.id: option for option in options}
    if any(option_id not in options_by_id for option_id in option_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")
    for item_in in estimate_in.items:
        if not _option_is_admin_usable(options_by_id[item_in.option_id]):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Option cannot be used")
    try:
        return estimate_crud.update_admin_consultation_estimate(db, estimate, estimate_in, options_by_id)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)
    except Exception as exc:
        _handle_unexpected_error(db, exc)

@router.put(
    "/{estimate_id}/items",
    response_model=EstimateDetailResponse,
    summary="Replace estimate items",
    dependencies=[Depends(get_current_admin)],
    responses={404: {"description": "Estimate or option not found"}, 409: {"description": "Only draft estimates can be edited, or option cannot be used"}},
)
def replace_estimate_items(estimate_id: int, items_in: EstimateItemsReplace, db: DbSession) -> EstimateDetailResponse:
    estimate = estimate_crud.get_estimate(db, estimate_id)
    if estimate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estimate not found")
    if estimate.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only draft estimates can be edited")

    existing_option_ids = {item.option_id for item in estimate.items if item.option_id is not None}
    options_by_id = _load_options_or_raise(db, items_in.items, existing_option_ids=existing_option_ids)
    try:
        return estimate_crud.replace_estimate_items(db, estimate, items_in, options_by_id)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)
    except Exception as exc:
        _handle_unexpected_error(db, exc)

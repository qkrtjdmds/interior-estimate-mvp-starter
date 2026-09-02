from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.crud import estimate as estimate_crud
from app.db.session import get_db
from app.schemas.estimate import (
    ALLOWED_ESTIMATE_STATUSES,
    EstimateCreate,
    EstimateDetailResponse,
    EstimateItemsReplace,
    EstimateListResponse,
    EstimateUpdate,
)

router = APIRouter(prefix="/api/estimates", tags=["estimates"])
DbSession = Annotated[Session, Depends(get_db)]

ALLOWED_STATUS_TRANSITIONS = {
    "draft": {"draft", "submitted", "cancelled"},
    "submitted": {"submitted", "draft", "confirmed", "cancelled"},
    "confirmed": {"confirmed", "cancelled"},
    "cancelled": {"cancelled"},
}
BASIC_UPDATE_FIELDS = {"customer_name", "customer_phone", "project_address", "notes", "valid_until"}


def _handle_unexpected_error(db: Session, exc: Exception) -> None:
    db.rollback()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database operation failed",
    ) from exc


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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status cannot be patched with other fields",
        )

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


def _load_options_or_raise(db: Session, item_requests) -> dict[int, object]:
    option_ids = [item.option_id for item in item_requests]
    options = estimate_crud.get_options_for_estimate(db, option_ids)
    options_by_id = {option.id: option for option in options}

    if any(option_id not in options_by_id for option_id in option_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")
    if any(not option.active for option in options):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inactive option cannot be used")
    return options_by_id


@router.post(
    "",
    response_model=EstimateDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create estimate",
    responses={404: {"description": "Option not found"}, 409: {"description": "Inactive option or DB conflict"}},
)
def create_estimate(estimate_in: EstimateCreate, db: DbSession) -> EstimateDetailResponse:
    options_by_id = _load_options_or_raise(db, estimate_in.items)

    try:
        return estimate_crud.create_estimate(db, estimate_in, options_by_id)
    except estimate_crud.EstimateNumberGenerationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not generate unique estimate number",
        ) from exc
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)
    except Exception as exc:
        _handle_unexpected_error(db, exc)


@router.get("", response_model=list[EstimateListResponse], summary="List estimates")
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
    return estimate_crud.get_estimates(
        db,
        status=status,
        customer_name=customer_name,
        estimate_number=estimate_number,
        created_from=created_from,
        created_to=created_to,
        skip=skip,
        limit=limit,
    )


@router.get("/{estimate_id}", response_model=EstimateDetailResponse, summary="Get estimate")
def get_estimate(estimate_id: int, db: DbSession) -> EstimateDetailResponse:
    estimate = estimate_crud.get_estimate(db, estimate_id)
    if estimate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estimate not found")
    return estimate


@router.patch(
    "/{estimate_id}",
    response_model=EstimateDetailResponse,
    summary="Update estimate",
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
        return estimate_crud.update_estimate(db, estimate, estimate_in)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)
    except Exception as exc:
        _handle_unexpected_error(db, exc)


@router.put(
    "/{estimate_id}/items",
    response_model=EstimateDetailResponse,
    summary="Replace estimate items",
    responses={
        404: {"description": "Estimate or option not found"},
        409: {"description": "Only draft estimates can be edited, or inactive option"},
    },
)
def replace_estimate_items(
    estimate_id: int,
    items_in: EstimateItemsReplace,
    db: DbSession,
) -> EstimateDetailResponse:
    estimate = estimate_crud.get_estimate(db, estimate_id)
    if estimate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estimate not found")
    if estimate.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only draft estimates can be edited")

    options_by_id = _load_options_or_raise(db, items_in.items)
    try:
        return estimate_crud.replace_estimate_items(db, estimate, items_in, options_by_id)
    except SQLAlchemyError as exc:
        _handle_db_error(db, exc)
    except Exception as exc:
        _handle_unexpected_error(db, exc)
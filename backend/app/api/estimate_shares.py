from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin
from app.crud import estimate as estimate_crud
from app.crud import estimate_share as share_crud
from app.db.session import get_db
from app.models import AdminUser, EstimateShare
from app.schemas.estimate_share import (
    EstimateShareCreate,
    EstimateShareCreateResponse,
    EstimateShareStatusResponse,
    PublicEstimateItemResponse,
    PublicEstimateResponse,
)
from app.services.estimate_pdf import PdfFontConfigurationError, PdfGenerationError, PdfRenderOptions, build_estimate_pdf, sanitize_pdf_filename

router = APIRouter(tags=["estimate-shares"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[AdminUser, Depends(get_current_admin)]
ShareTokenHeader = Annotated[str | None, Header(alias="X-Estimate-Share-Token")]

PUBLIC_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


def _db_error(db: Session, exc: SQLAlchemyError) -> None:
    db.rollback()
    if isinstance(exc, IntegrityError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Database constraint violation") from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed") from exc


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(expires_at: datetime) -> bool:
    expires = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    return expires <= _utc_now()


def _load_public_share(db: Session, share_token: str | None, *, record_access: bool) -> EstimateShare:
    if not share_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Share token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    share = share_crud.get_share_by_token(db, share_token)
    if share is None or not share.active or share.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared estimate not found")
    if _is_expired(share.expires_at):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Shared estimate is expired")

    estimate = share.estimate
    if estimate.status == "cancelled":
        try:
            share_crud.revoke_share(db, share)
        except SQLAlchemyError as exc:
            _db_error(db, exc)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared estimate not found")
    if estimate.status not in share_crud.PUBLIC_READABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared estimate not found")

    if record_access:
        try:
            share_crud.record_share_access(db, share)
        except SQLAlchemyError as exc:
            _db_error(db, exc)
    return share


def _build_public_estimate_response(share: EstimateShare) -> PublicEstimateResponse:
    estimate = share.estimate
    return PublicEstimateResponse(
        estimate_number=estimate.estimate_number,
        status=estimate.status,
        customer_name_masked=share_crud.mask_customer_name(estimate.customer_name),
        created_at=estimate.created_at,
        valid_until=estimate.valid_until,
        items=[
            PublicEstimateItemResponse(
                category_name=item.category_name_snapshot,
                item_name=item.item_name_snapshot,
                option_name=item.option_name_snapshot,
                description=item.description_snapshot,
                unit=item.unit_snapshot,
                unit_price=item.unit_price_snapshot,
                quantity=item.quantity,
                line_total=item.line_total,
                sort_order=item.sort_order,
            )
            for item in estimate.items
        ],
        subtotal=estimate.subtotal,
        vat_rate=estimate.vat_rate,
        vat_amount=estimate.vat_amount,
        total_amount=estimate.total_amount,
    )


@router.post(
    "/api/estimates/{estimate_id}/share",
    response_model=EstimateShareCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create estimate share token",
)
def create_estimate_share(
    estimate_id: int,
    db: DbSession,
    current_admin: CurrentAdmin,
    share_in: EstimateShareCreate = EstimateShareCreate(),
) -> EstimateShareCreateResponse:
    estimate = estimate_crud.get_estimate(db, estimate_id)
    if estimate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estimate not found")
    if estimate.status not in share_crud.SHAREABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Estimate cannot be shared")
    try:
        share, raw_token = share_crud.create_share(db, estimate, share_in.expires_in_days)
    except SQLAlchemyError as exc:
        _db_error(db, exc)
    return EstimateShareCreateResponse(share_token=raw_token, expires_at=share.expires_at, created_at=share.created_at)


@router.get(
    "/api/estimates/{estimate_id}/share",
    response_model=EstimateShareStatusResponse,
    summary="Get active estimate share status",
)
def get_estimate_share_status(estimate_id: int, db: DbSession, current_admin: CurrentAdmin) -> EstimateShareStatusResponse:
    estimate = estimate_crud.get_estimate(db, estimate_id)
    if estimate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estimate not found")
    share = share_crud.get_active_share_for_estimate(db, estimate_id)
    if share is None:
        return EstimateShareStatusResponse(active=False)
    return share


@router.delete(
    "/api/estimates/{estimate_id}/share",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke active estimate share",
)
def revoke_estimate_share(estimate_id: int, db: DbSession, current_admin: CurrentAdmin) -> Response:
    try:
        share_crud.revoke_active_shares_for_estimate(db, estimate_id)
        db.commit()
    except SQLAlchemyError as exc:
        _db_error(db, exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/api/public/estimate",
    response_model=PublicEstimateResponse,
    summary="Get shared estimate",
)
def get_public_estimate(db: DbSession, share_token: ShareTokenHeader = None) -> Response:
    share = _load_public_share(db, share_token, record_access=True)
    response = _build_public_estimate_response(share)
    return Response(content=response.model_dump_json(), media_type="application/json", headers=PUBLIC_SECURITY_HEADERS)


@router.get(
    "/api/public/estimate/pdf",
    summary="Download shared estimate PDF",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF file"},
        401: {"description": "Share token is required"},
        404: {"description": "Shared estimate not found"},
        410: {"description": "Shared estimate is expired"},
        503: {"description": "PDF font is not configured"},
    },
)
def download_public_estimate_pdf(db: DbSession, share_token: ShareTokenHeader = None) -> Response:
    share = _load_public_share(db, share_token, record_access=True)
    try:
        pdf_bytes = build_estimate_pdf(share.estimate, PdfRenderOptions(public=True))
    except PdfFontConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="PDF font is not configured") from exc
    except PdfGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PDF generation failed") from exc

    filename = sanitize_pdf_filename(share.estimate.estimate_number)
    headers = {
        **PUBLIC_SECURITY_HEADERS,
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Estimate, EstimateItem, Item, Option
from app.schemas.estimate import EstimateAdminConsultationUpdate, EstimateCreate, EstimateItemsReplace, EstimateUpdate
from app.services.estimate_calculator import DEFAULT_VAT_RATE, calculate_line_total, calculate_totals


class EstimateNumberGenerationError(Exception):
    pass


def generate_estimate_number() -> str:
    now = datetime.now()
    return f"EST-{now:%Y%m%d}-{uuid4().hex[:8].upper()}"


def get_estimate(db: Session, estimate_id: int) -> Estimate | None:
    statement = select(Estimate).options(selectinload(Estimate.items)).where(Estimate.id == estimate_id)
    return db.scalar(statement)


def get_estimates(
    db: Session,
    *,
    status: str | None = None,
    customer_name: str | None = None,
    estimate_number: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Estimate]:
    statement = select(Estimate)
    if status is not None:
        statement = statement.where(Estimate.status == status)
    if customer_name:
        statement = statement.where(Estimate.customer_name.ilike(f"%{customer_name}%"))
    if estimate_number:
        statement = statement.where(Estimate.estimate_number.ilike(f"%{estimate_number}%"))
    if created_from is not None:
        statement = statement.where(Estimate.created_at >= created_from)
    if created_to is not None:
        statement = statement.where(Estimate.created_at <= created_to)
    statement = statement.order_by(Estimate.created_at.desc(), Estimate.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_options_for_estimate(db: Session, option_ids: list[int]) -> list[Option]:
    statement = select(Option).options(joinedload(Option.item).joinedload(Item.category)).where(Option.id.in_(option_ids))
    return list(db.scalars(statement).all())


def recalculate_estimate_totals(estimate: Estimate) -> None:
    line_totals = []
    for item in estimate.items:
        item.line_total = calculate_line_total(item.unit_price_snapshot, item.quantity)
        line_totals.append(item.line_total)
    estimate.subtotal, estimate.vat_amount, estimate.total_amount = calculate_totals(line_totals, estimate.vat_rate)


def _new_estimate_item(option: Option, quantity: Decimal, sort_order: int) -> EstimateItem:
    return EstimateItem(
        option_id=option.id,
        category_name_snapshot=option.item.category.name,
        item_name_snapshot=option.item.name,
        option_name_snapshot=option.name,
        description_snapshot=option.description,
        unit_snapshot=option.unit,
        unit_price_snapshot=option.default_price,
        quantity=quantity,
        line_total=calculate_line_total(option.default_price, quantity),
        sort_order=sort_order,
    )


def _build_estimate_items(estimate_in: EstimateCreate, options_by_id: dict[int, Option]) -> tuple[list[EstimateItem], list[Decimal]]:
    estimate_items: list[EstimateItem] = []
    line_totals: list[Decimal] = []

    for item_in in estimate_in.items:
        option = options_by_id[item_in.option_id]
        estimate_item = _new_estimate_item(option, item_in.quantity, item_in.sort_order)
        estimate_items.append(estimate_item)
        line_totals.append(estimate_item.line_total)

    return estimate_items, line_totals


def create_estimate(db: Session, estimate_in: EstimateCreate, options_by_id: dict[int, Option]) -> Estimate:
    for _ in range(5):
        estimate_items, line_totals = _build_estimate_items(estimate_in, options_by_id)
        subtotal, vat_amount, total_amount = calculate_totals(line_totals, DEFAULT_VAT_RATE)
        estimate = Estimate(
            estimate_number=generate_estimate_number(),
            customer_name=estimate_in.customer_name.strip(),
            customer_phone=estimate_in.customer_phone,
            customer_email=estimate_in.customer_email,
            housing_type=estimate_in.housing_type,
            floor_area_pyeong=estimate_in.floor_area_pyeong,
            renovation_scope=estimate_in.renovation_scope,
            preferred_timeline=estimate_in.preferred_timeline,
            project_address=estimate_in.project_address,
            status="draft",
            notes=estimate_in.notes,
            subtotal=subtotal,
            vat_rate=DEFAULT_VAT_RATE,
            vat_amount=vat_amount,
            total_amount=total_amount,
            valid_until=estimate_in.valid_until,
            items=estimate_items,
        )
        db.add(estimate)
        try:
            db.commit()
            db.refresh(estimate)
            return get_estimate(db, estimate.id) or estimate
        except IntegrityError:
            db.rollback()

    raise EstimateNumberGenerationError("failed to generate unique estimate number")


def replace_estimate_items(
    db: Session,
    estimate: Estimate,
    items_in: EstimateItemsReplace,
    options_by_id: dict[int, Option],
) -> Estimate:
    existing_by_option_id = {item.option_id: item for item in estimate.items if item.option_id is not None}
    requested_option_ids = {item.option_id for item in items_in.items}

    for existing_item in list(estimate.items):
        if existing_item.option_id not in requested_option_ids:
            db.delete(existing_item)
            estimate.items.remove(existing_item)

    for item_in in items_in.items:
        existing_item = existing_by_option_id.get(item_in.option_id)
        if existing_item is not None:
            existing_item.quantity = item_in.quantity
            existing_item.sort_order = item_in.sort_order
            existing_item.line_total = calculate_line_total(existing_item.unit_price_snapshot, item_in.quantity)
        else:
            estimate.items.append(_new_estimate_item(options_by_id[item_in.option_id], item_in.quantity, item_in.sort_order))

    recalculate_estimate_totals(estimate)
    db.add(estimate)
    db.commit()
    db.refresh(estimate)
    return get_estimate(db, estimate.id) or estimate


def update_admin_consultation_estimate(
    db: Session,
    estimate: Estimate,
    estimate_in: EstimateAdminConsultationUpdate,
    options_by_id: dict[int, Option],
) -> Estimate:
    for existing_item in list(estimate.items):
        db.delete(existing_item)
        estimate.items.remove(existing_item)
    db.flush()

    estimate.items = [
        _new_estimate_item(options_by_id[item_in.option_id], item_in.quantity, item_in.sort_order)
        for item_in in estimate_in.items
    ]
    estimate.housing_type = estimate_in.housing_type
    estimate.floor_area_pyeong = estimate_in.floor_area_pyeong
    estimate.renovation_scope = estimate_in.renovation_scope
    estimate.preferred_timeline = estimate_in.preferred_timeline
    estimate.project_address = estimate_in.project_address
    estimate.admin_consultation_note = estimate_in.admin_consultation_note
    estimate.updated_at = datetime.now(timezone.utc)
    recalculate_estimate_totals(estimate)
    db.add(estimate)
    db.commit()
    db.refresh(estimate)
    return get_estimate(db, estimate.id) or estimate

def update_estimate(db: Session, estimate: Estimate, estimate_in: EstimateUpdate) -> Estimate:
    for field, value in estimate_in.model_dump(exclude_unset=True).items():
        if field == "customer_name" and value is not None:
            value = value.strip()
        setattr(estimate, field, value)
    recalculate_estimate_totals(estimate)
    db.add(estimate)
    db.commit()
    db.refresh(estimate)
    return get_estimate(db, estimate.id) or estimate

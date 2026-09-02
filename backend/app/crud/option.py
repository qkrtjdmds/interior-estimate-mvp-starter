from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reference import Item, Option
from app.schemas.option import OptionCreate, OptionUpdate


def get_option(db: Session, option_id: int) -> Option | None:
    return db.get(Option, option_id)


def item_exists(db: Session, item_id: int) -> bool:
    return db.get(Item, item_id) is not None


def get_options(
    db: Session,
    *,
    item_id: int | None = None,
    active: bool | None = None,
    customer_visible: bool | None = None,
    recommended: bool | None = None,
    unit: str | None = None,
    name: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Option]:
    statement = select(Option)
    if item_id is not None:
        statement = statement.where(Option.item_id == item_id)
    if active is not None:
        statement = statement.where(Option.active == active)
    if customer_visible is not None:
        statement = statement.where(Option.customer_visible == customer_visible)
    if recommended is not None:
        statement = statement.where(Option.recommended == recommended)
    if unit:
        statement = statement.where(Option.unit == unit)
    if name:
        statement = statement.where(Option.name.ilike(f"%{name}%"))
    statement = statement.order_by(Option.sort_order.asc(), Option.id.asc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def create_option(db: Session, option_in: OptionCreate) -> Option:
    option = Option(**option_in.model_dump())
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


def update_option(db: Session, option: Option, option_in: OptionUpdate) -> Option:
    for field, value in option_in.model_dump(exclude_unset=True).items():
        setattr(option, field, value)
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


def delete_option(db: Session, option: Option) -> None:
    db.delete(option)
    db.commit()
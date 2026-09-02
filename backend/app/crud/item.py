from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.reference import Category, Item, Option
from app.schemas.item import ItemCreate, ItemUpdate


def get_item(db: Session, item_id: int) -> Item | None:
    return db.get(Item, item_id)


def category_exists(db: Session, category_id: int) -> bool:
    return db.get(Category, category_id) is not None


def get_items(
    db: Session,
    *,
    category_id: int | None = None,
    active: bool | None = None,
    customer_visible: bool | None = None,
    name: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Item]:
    statement = select(Item)
    if category_id is not None:
        statement = statement.where(Item.category_id == category_id)
    if active is not None:
        statement = statement.where(Item.active == active)
    if customer_visible is not None:
        statement = statement.where(Item.customer_visible == customer_visible)
    if name:
        statement = statement.where(Item.name.ilike(f"%{name}%"))
    statement = statement.order_by(Item.sort_order.asc(), Item.id.asc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def create_item(db: Session, item_in: ItemCreate) -> Item:
    item = Item(**item_in.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item: Item, item_in: ItemUpdate) -> Item:
    for field, value in item_in.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def item_has_options(db: Session, item_id: int) -> bool:
    statement = select(func.count()).select_from(Option).where(Option.item_id == item_id)
    return db.scalar(statement) > 0


def delete_item(db: Session, item: Item) -> None:
    db.delete(item)
    db.commit()
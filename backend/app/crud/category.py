from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.reference import Category, Item
from app.schemas.category import CategoryCreate, CategoryUpdate


def get_category(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def get_categories(
    db: Session,
    *,
    active: bool | None = None,
    customer_visible: bool | None = None,
    name: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Category]:
    statement = select(Category)
    if active is not None:
        statement = statement.where(Category.active == active)
    if customer_visible is not None:
        statement = statement.where(Category.customer_visible == customer_visible)
    if name:
        statement = statement.where(Category.name.ilike(f"%{name}%"))
    statement = statement.order_by(Category.sort_order.asc(), Category.id.asc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def create_category(db: Session, category_in: CategoryCreate) -> Category:
    category = Category(**category_in.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category: Category, category_in: CategoryUpdate) -> Category:
    for field, value in category_in.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def category_has_items(db: Session, category_id: int) -> bool:
    statement = select(func.count()).select_from(Item).where(Item.category_id == category_id)
    return db.scalar(statement) > 0


def delete_category(db: Session, category: Category) -> None:
    db.delete(category)
    db.commit()
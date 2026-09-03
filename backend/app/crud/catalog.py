from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Item, Option
from app.schemas.catalog import CatalogCategoryResponse, CatalogItemResponse, CatalogOptionResponse


def get_customer_catalog(db: Session) -> list[CatalogCategoryResponse]:
    categories = db.scalars(
        select(Category)
        .where(Category.active.is_(True), Category.customer_visible.is_(True))
        .order_by(Category.sort_order.asc(), Category.id.asc())
    ).all()
    if not categories:
        return []

    category_ids = [category.id for category in categories]
    items = db.scalars(
        select(Item)
        .where(
            Item.category_id.in_(category_ids),
            Item.active.is_(True),
            Item.customer_visible.is_(True),
        )
        .order_by(Item.sort_order.asc(), Item.id.asc())
    ).all()
    if not items:
        return []

    item_ids = [item.id for item in items]
    options = db.scalars(
        select(Option)
        .where(
            Option.item_id.in_(item_ids),
            Option.active.is_(True),
            Option.customer_visible.is_(True),
        )
        .order_by(Option.sort_order.asc(), Option.id.asc())
    ).all()

    options_by_item_id: dict[int, list[CatalogOptionResponse]] = {}
    for option in options:
        options_by_item_id.setdefault(option.item_id, []).append(
            CatalogOptionResponse.model_validate(option)
        )

    items_by_category_id: dict[int, list[CatalogItemResponse]] = {}
    for item in items:
        item_options = options_by_item_id.get(item.id, [])
        if not item_options:
            continue
        items_by_category_id.setdefault(item.category_id, []).append(
            CatalogItemResponse(
                id=item.id,
                name=item.name,
                description=item.description,
                sort_order=item.sort_order,
                options=item_options,
            )
        )

    catalog: list[CatalogCategoryResponse] = []
    for category in categories:
        category_items = items_by_category_id.get(category.id, [])
        if not category_items:
            continue
        catalog.append(
            CatalogCategoryResponse(
                id=category.id,
                name=category.name,
                description=category.description,
                sort_order=category.sort_order,
                items=category_items,
            )
        )
    return catalog
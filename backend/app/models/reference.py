from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VisibilityMixin:
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    customer_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Category(TimestampMixin, VisibilityMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("uq_categories_normalized_name", func.lower(func.btrim(name)), unique=True).ddl_if(dialect="postgresql"),
    )

    items: Mapped[list["Item"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
    )


class Item(TimestampMixin, VisibilityMixin, Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("uq_items_category_normalized_name", category_id, func.lower(func.btrim(name)), unique=True).ddl_if(
            dialect="postgresql"
        ),
    )

    category: Mapped[Category] = relationship(back_populates="items")
    options: Mapped[list["Option"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
    )


class Option(TimestampMixin, VisibilityMixin, Base):
    __tablename__ = "options"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    default_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("uq_options_item_normalized_name", item_id, func.lower(func.btrim(name)), unique=True).ddl_if(
            dialect="postgresql"
        ),
    )

    item: Mapped[Item] = relationship(back_populates="options")
    estimate_items: Mapped[list["EstimateItem"]] = relationship(back_populates="option")
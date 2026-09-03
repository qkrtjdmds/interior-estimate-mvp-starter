from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Estimate(Base):
    __tablename__ = "estimates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    estimate_number: Mapped[str] = mapped_column(String(40), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_phone: Mapped[str | None] = mapped_column(String(50))
    customer_email: Mapped[str | None] = mapped_column(String(255))
    housing_type: Mapped[str | None] = mapped_column(String(50))
    floor_area_pyeong: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    renovation_scope: Mapped[str | None] = mapped_column(String(50))
    preferred_timeline: Mapped[str | None] = mapped_column(String(50))
    project_address: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("estimate_number"),
        CheckConstraint("subtotal >= 0", name="ck_estimates_subtotal_non_negative"),
        CheckConstraint("vat_rate >= 0", name="ck_estimates_vat_rate_non_negative"),
        CheckConstraint("vat_amount >= 0", name="ck_estimates_vat_amount_non_negative"),
        CheckConstraint("total_amount >= 0", name="ck_estimates_total_amount_non_negative"),
        Index("ix_estimates_estimate_number", "estimate_number"),
    )

    shares: Mapped[list["EstimateShare"]] = relationship(
        back_populates="estimate",
        cascade="all, delete-orphan",
    )

    items: Mapped[list["EstimateItem"]] = relationship(
        back_populates="estimate",
        cascade="all, delete-orphan",
        order_by="EstimateItem.sort_order, EstimateItem.id",
    )


class EstimateItem(Base):
    __tablename__ = "estimate_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    estimate_id: Mapped[int] = mapped_column(
        ForeignKey("estimates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    option_id: Mapped[int | None] = mapped_column(
        ForeignKey("options.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    item_name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    option_name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    description_snapshot: Mapped[str | None] = mapped_column(Text)
    unit_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
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

    estimate: Mapped[Estimate] = relationship(back_populates="items")
    option: Mapped["Option | None"] = relationship(back_populates="estimate_items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_estimate_items_quantity_positive"),
        CheckConstraint("line_total >= 0", name="ck_estimate_items_line_total_non_negative"),
        Index("ix_estimate_items_estimate_sort_id", "estimate_id", "sort_order", "id"),
        Index(
            "uq_estimate_items_estimate_option",
            "estimate_id",
            "option_id",
            unique=True,
            postgresql_where=option_id.is_not(None),
        ),
    )

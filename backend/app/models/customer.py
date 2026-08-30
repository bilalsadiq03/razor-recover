from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Numeric,
    String,
    Integer,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)

    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id"),
        nullable=False,
        index=True,
    )

    external_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    customer_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    total_orders: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    successful_payments: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    failed_payments: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    lifetime_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    merchant = relationship(
        "Merchant",
        back_populates="customers",
    )

    orders = relationship(
        "Order",
        back_populates="customer",
    )

    payments = relationship(
        "Payment",
        back_populates="customer",
    )
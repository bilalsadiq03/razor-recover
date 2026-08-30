from datetime import datetime
from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.core.database import Base

class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    external_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    
    customers = relationship(
        "Customer",
        back_populates="merchant",
        cascade="all, delete-orphan",
        lazy="noload"
    )

    orders = relationship(
        "Order",
        back_populates="merchant",
    )
    
    
    
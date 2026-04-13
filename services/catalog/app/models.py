from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, String, Text, Boolean, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from .database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    # Foreign key conceptually, but we don't enforce DB constraint here since Vendor Service is disjoint.
    vendor_id = Column(String, index=True, nullable=False)
    
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(100), index=True, nullable=False)
    image_url = Column(String(500), nullable=True)
    
    is_active = Column(Boolean, default=True, index=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

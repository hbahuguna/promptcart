from datetime import datetime, timezone
import uuid
import enum

from sqlalchemy import Column, String, Text, Boolean, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from .database import Base


class VendorTypeEnum(str, enum.Enum):
    DARK_STORE = "DARK_STORE"
    SHOPKEEPER = "SHOPKEEPER"


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    name = Column(String, index=True, nullable=False)
    type = Column(Enum(VendorTypeEnum), nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

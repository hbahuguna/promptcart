from decimal import Decimal
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    vendor_id: str = Field(..., description="UUID of the Vendor")
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., decimal_places=2)
    category: str = Field(..., max_length=100)
    image_url: Optional[str] = Field(None, max_length=500)
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, decimal_places=2)
    category: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

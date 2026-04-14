from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from decimal import Decimal
from uuid import UUID
from datetime import datetime

class OrderItemBase(BaseModel):
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemResponse(OrderItemBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

class OrderBase(BaseModel):
    customer_whatsapp_number: str
    vendor_id: UUID
    total_amount: Decimal
    delivery_address: str
    
class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderUpdate(BaseModel):
    status: Optional[str] = None

class OrderResponse(OrderBase):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []
    model_config = ConfigDict(from_attributes=True)

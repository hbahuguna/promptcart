from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from .models import VendorTypeEnum


class VendorBase(BaseModel):
    name: str
    type: VendorTypeEnum
    phone_number: str
    address: Optional[str] = None
    is_active: bool = True


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[VendorTypeEnum] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class VendorResponse(VendorBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

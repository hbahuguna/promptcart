from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/v1/vendors", tags=["Vendors"])


@router.post("", response_model=schemas.VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    vendor: schemas.VendorCreate,
    db: AsyncSession = Depends(get_db),
):
    # Check if phone number already exists
    stmt = select(models.Vendor).where(models.Vendor.phone_number == vendor.phone_number)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor with this phone number already exists",
        )

    db_vendor = models.Vendor(**vendor.model_dump())
    db.add(db_vendor)
    await db.commit()
    await db.refresh(db_vendor)
    return db_vendor


@router.get("", response_model=List[schemas.VendorResponse])
async def list_vendors(
    type: Optional[models.VendorTypeEnum] = Query(None, description="Filter by DARK_STORE or SHOPKEEPER"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(models.Vendor)
    if type:
        stmt = stmt.where(models.Vendor.type == type)

    result = await db.execute(stmt)
    vendors = result.scalars().all()
    return vendors


@router.get("/{vendor_id}", response_model=schemas.VendorResponse)
async def get_vendor(vendor_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(models.Vendor).where(models.Vendor.id == vendor_id)
    result = await db.execute(stmt)
    db_vendor = result.scalars().first()

    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    return db_vendor


@router.patch("/{vendor_id}", response_model=schemas.VendorResponse)
async def update_vendor(
    vendor_id: str,
    vendor_update: schemas.VendorUpdate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(models.Vendor).where(models.Vendor.id == vendor_id)
    result = await db.execute(stmt)
    db_vendor = result.scalars().first()

    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    update_data = vendor_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_vendor, key, value)

    await db.commit()
    await db.refresh(db_vendor)
    return db_vendor


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
):
    # Soft delete
    stmt = select(models.Vendor).where(models.Vendor.id == vendor_id)
    result = await db.execute(stmt)
    db_vendor = result.scalars().first()

    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    db_vendor.is_active = False
    await db.commit()
    return None

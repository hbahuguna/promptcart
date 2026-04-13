from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.post("", response_model=schemas.ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: schemas.ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.get("", response_model=List[schemas.ProductResponse])
async def list_products(
    vendor_id: Optional[str] = Query(None, description="Filter by Vendor ID"),
    category: Optional[str] = Query(None, description="Filter by Category"),
    include_inactive: bool = Query(False, description="Whether to include soft-deleted products"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(models.Product)
    
    if not include_inactive:
        stmt = stmt.where(models.Product.is_active == True)
        
    if vendor_id:
        stmt = stmt.where(models.Product.vendor_id == vendor_id)
        
    if category:
        stmt = stmt.where(models.Product.category == category)

    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    products = result.scalars().all()
    return products


@router.get("/vendor/{vendor_id}", response_model=List[schemas.ProductResponse])
async def list_products_by_vendor(
    vendor_id: str,
    include_inactive: bool = Query(False, description="Whether to include soft-deleted products"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(models.Product).where(models.Product.vendor_id == vendor_id)
    
    if not include_inactive:
        stmt = stmt.where(models.Product.is_active == True)

    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    products = result.scalars().all()
    return products


@router.get("/{product_id}", response_model=schemas.ProductResponse)
async def get_product(
    product_id: str,
    include_inactive: bool = Query(False, description="Include product if soft-deleted"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(models.Product).where(models.Product.id == product_id)
    if not include_inactive:
        stmt = stmt.where(models.Product.is_active == True)
        
    result = await db.execute(stmt)
    db_product = result.scalars().first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found or inactive")

    return db_product


@router.patch("/{product_id}", response_model=schemas.ProductResponse)
async def update_product(
    product_id: str,
    product_update: schemas.ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(models.Product).where(models.Product.id == product_id)
    result = await db.execute(stmt)
    db_product = result.scalars().first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    # Soft delete sets is_active=False
    stmt = select(models.Product).where(models.Product.id == product_id)
    result = await db.execute(stmt)
    db_product = result.scalars().first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db_product.is_active = False
    await db.commit()
    return None

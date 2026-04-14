from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime, timezone

from app import models, schemas, database, events

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])

@router.post("", response_model=schemas.OrderResponse)
async def create_order(order: schemas.OrderCreate, db: AsyncSession = Depends(database.get_db)):
    """
    Validates cart contents extracting individual relationships into database maps and publishing downstream.
    """
    db_order = models.Order(
        customer_whatsapp_number=order.customer_whatsapp_number,
        vendor_id=order.vendor_id,
        total_amount=order.total_amount,
        delivery_address=order.delivery_address
    )
    db.add(db_order)
    await db.flush() # Extract PK local binding sequence
    
    for item in order.items:
        db_item = models.OrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price
        )
        db.add(db_item)
    
    await db.commit()
    await db.refresh(db_order)
    
    # Reload mapping relationships explicitly
    stmt = select(models.Order).options(selectinload(models.Order.items)).where(models.Order.id == db_order.id)
    result = await db.execute(stmt)
    full_order = result.scalar_one()

    # Create event payload mapping exact native layout request
    event_payload = {
        "order_id": str(full_order.id),
        "vendor_id": str(full_order.vendor_id),
        "customer_whatsapp_number": full_order.customer_whatsapp_number,
        "items": [
            {
                "product_id": str(i.product_id), 
                "product_name": i.product_name,
                "quantity": float(i.quantity),
                "price": float(i.unit_price)
            } for i in full_order.items
        ],
        "delivery_address": full_order.delivery_address, # Persists JSON implicitly because we capture structured lists upstream
        "total_amount": float(full_order.total_amount)
    }
    
    await events.publish_order_created(event_payload)
    return full_order

@router.get("/{order_id}", response_model=schemas.OrderResponse)
async def get_order(order_id: UUID, db: AsyncSession = Depends(database.get_db)):
    stmt = select(models.Order).options(selectinload(models.Order.items)).where(models.Order.id == order_id)
    result = await db.execute(stmt)
    db_order = result.scalar_one_or_none()
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

@router.get("", response_model=list[schemas.OrderResponse])
async def list_orders(customer_whatsapp_number: str = None, db: AsyncSession = Depends(database.get_db)):
    stmt = select(models.Order).options(selectinload(models.Order.items))
    if customer_whatsapp_number:
        stmt = stmt.where(models.Order.customer_whatsapp_number == customer_whatsapp_number)
    result = await db.execute(stmt)
    return result.scalars().all()
    
@router.patch("/{order_id}/status", response_model=schemas.OrderResponse)
async def update_order_status(order_id: UUID, update: dict, db: AsyncSession = Depends(database.get_db)):
    if "status" not in update:
        raise HTTPException(status_code=400, detail="Missing status field")
        
    stmt = select(models.Order).options(selectinload(models.Order.items)).where(models.Order.id == order_id)
    result = await db.execute(stmt)
    db_order = result.scalar_one_or_none()
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
        
    db_order.status = update["status"]
    db_order.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_order)
    return db_order

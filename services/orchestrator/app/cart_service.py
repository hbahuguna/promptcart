import os
import json
import logging
from redis import asyncio as aioredis

logger = logging.getLogger("orchestrator_cart")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Global connection to minimize overhead; instantiated organically by functions
_redis_pool = aioredis.from_url(REDIS_URL, decode_responses=True)

def _get_cart_key(whatsapp_number: str) -> str:
    return f"cart:{whatsapp_number}"

async def add_to_cart(whatsapp_number: str, product_id: str, qty: int = 1):
    """
    Upserts an item to the user's cart in Redis Hash Set
    """
    try:
        cart_key = _get_cart_key(whatsapp_number)
        await _redis_pool.hincrby(cart_key, product_id, qty)
        logger.info(f"Added {qty} of {product_id} to cart for {whatsapp_number}")
    except Exception as e:
        logger.error(f"Redis Add To Cart Error: {e}")

async def get_cart(whatsapp_number: str) -> dict:
    """
    Returns the user's cart
    {'product_id_1': 'qty', 'product_id_2': 'qty'}
    """
    try:
        cart_key = _get_cart_key(whatsapp_number)
        cart = await _redis_pool.hgetall(cart_key)
        # Parse quantities to int
        return {k: int(v) for k, v in cart.items()}
    except Exception as e:
        logger.error(f"Redis Get Cart Error: {e}")
        return {}

async def clear_cart(whatsapp_number: str):
    """
    Deletes the Redis hash
    """
    try:
        cart_key = _get_cart_key(whatsapp_number)
        await _redis_pool.delete(cart_key)
        logger.info(f"Cleared cart for {whatsapp_number}")
    except Exception as e:
        logger.error(f"Redis Clear Cart Error: {e}")

async def remove_item(whatsapp_number: str, product_id: str):
    """
    Deletes a specific product code from the cart hash.
    """
    try:
        cart_key = _get_cart_key(whatsapp_number)
        await _redis_pool.hdel(cart_key, product_id)
        logger.info(f"Removed item {product_id} from {whatsapp_number} cart")
    except Exception as e:
        logger.error(f"Failed to remove {product_id}: {e}")

async def update_quantity(whatsapp_number: str, product_id: str, new_qty: int):
    """
    Overrides the quantity to an exact new integer.
    """
    try:
        cart_key = _get_cart_key(whatsapp_number)
        if new_qty <= 0:
            await remove_item(whatsapp_number, product_id)
        else:
            await _redis_pool.hset(cart_key, product_id, new_qty)
            logger.info(f"Set item {product_id} to quantity {new_qty} for {whatsapp_number}")
    except Exception as e:
        logger.error(f"Failed to update quantity to {new_qty}: {e}")

async def get_cart_summary(whatsapp_number: str) -> dict:
    """
    Retrieves the raw cart, calls the Catalog via Network, and maps robust Decimal aggregates.
    Returns: { "items": [{...}], "total_price": float }
    """
    from decimal import Decimal
    from app import catalog_client
    
    raw_cart = await get_cart(whatsapp_number)
    
    items = []
    total_price = Decimal("0.00")
    
    for product_id, raw_qty in raw_cart.items():
        qty = int(raw_qty)
        # Verify the product data against standard DB configurations via network REST lookup
        product = await catalog_client.get_product_by_id(product_id)
        
        if not product:
            continue
            
        unit_price = Decimal(str(product.get("price", "0.00")))
        line_total = unit_price * qty
        total_price += line_total
        
        items.append({
            "product_id": product_id,
            "name": product.get("name", "Unknown Item"),
            "price": unit_price,
            "quantity": qty,
            "line_total": line_total
        })
        
    return {
        "items": items,
        "total_price": total_price
    }

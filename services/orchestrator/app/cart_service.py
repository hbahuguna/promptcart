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

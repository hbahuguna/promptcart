import os
import json
import redis.asyncio as redis
from decimal import Decimal

REDIS_URL = os.getenv("REDIS_URL", "redis://whatsapp-redis:6379")

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

_redis_pool = None

async def init_redis():
    global _redis_pool
    _redis_pool = redis.from_url(REDIS_URL, decode_responses=True)

async def close_redis():
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()

async def publish_order_created(payload: dict):
    """
    Broadcasts the completed checkout structures over the redis pub/sub mapping into fulfillment stubs
    """
    global _redis_pool
    if _redis_pool:
        await _redis_pool.publish("order.created", json.dumps(payload, cls=DecimalEncoder))

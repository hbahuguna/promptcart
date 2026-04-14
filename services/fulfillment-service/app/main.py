import asyncio
import os
import json
import logging
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("fulfillment_stub")

REDIS_URL = os.getenv("REDIS_URL", "redis://whatsapp-redis:6379")

async def listen_for_orders():
    """
    Subscribes to 'order.created' locally proving dispatch arrays securely
    """
    logger.info(f"Connecting to Redis at {REDIS_URL} for Fulfillment Stub...")
    r = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("order.created")
    
    logger.info("[FULFILLMENT] Listening for new orders on channel 'order.created'...")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    payload = json.loads(message["data"])
                    order_id = payload.get("order_id", "UNKNOWN")
                    vendor_id = payload.get("vendor_id", "UNKNOWN")
                    logger.info(f"[FULFILLMENT] Received order {order_id} for vendor {vendor_id}. Ready to notify store.")
                except Exception as e:
                    logger.error(f"Error parsing fulfillment message: {e}")
    except asyncio.CancelledError:
        logger.info("Shutting down fulfillment stub.")
    finally:
        await pubsub.close()
        await r.close()

if __name__ == "__main__":
    asyncio.run(listen_for_orders())

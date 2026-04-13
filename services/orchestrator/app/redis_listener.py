import os
import json
import asyncio
import logging
from redis import asyncio as aioredis
from app import whatsapp_client, catalog_client
from app.logger_utils import setup_logger, mask_phone

logger = setup_logger("orchestrator_redis")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
VENDOR_ID = os.environ.get("VENDOR_ID", "bab94c54-8035-4dbd-8b9e-252e0b08d304")

KEYWORDS = {"menu", "products", "catalog", "items", "show", "list"}

async def start_listener(stop_event: asyncio.Event):
    """
    Subscribes to Redis 'raw_whatsapp_messages' channel.
    Runs indefinitely until stop_event is set.
    """
    logger.info(f"Connecting to Redis at {REDIS_URL} for Orchestrator...")
    try:
        redis = await aioredis.from_url(REDIS_URL)
        pubsub = redis.pubsub()
        await pubsub.subscribe("raw_whatsapp_messages")
        
        logger.info("Subscribed to 'raw_whatsapp_messages'. Waiting for messages...")

        while not stop_event.is_set():
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    payload_raw = message["data"].decode("utf-8")
                    payload = json.loads(payload_raw)
                    await process_webhook(payload)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing pubsub message: {e}")
                await asyncio.sleep(1) # Prevent tight loop on crash
                
    except Exception as e:
        logger.error(f"Failed to connect or subscribe to Redis: {e}")
    finally:
        logger.info("Shutting down Redis listener...")

async def process_webhook(payload: dict):
    """
    Parses the deepest layers of the Meta webhook object.
    Matches text intent and coordinates external APIs.
    """
    try:
        entries = payload.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                
                for msg in messages:
                    sender = msg.get("from")
                    msg_type = msg.get("type", "unknown")
                    
                    if msg_type == "text":
                        text = msg.get("text", {}).get("body", "").strip()
                        if sender and text:
                            logger.info(f"From: {mask_phone(sender)} | Type: text | Content: {text[:50]}")
                            await route_message(sender, text)
                    elif msg_type == "interactive":
                        interactive_payload = msg.get("interactive", {})
                        if sender and interactive_payload:
                            i_type = interactive_payload.get("type")
                            i_id = interactive_payload.get(i_type, {}).get("id", "none")
                            logger.info(f"From: {mask_phone(sender)} | Type: interactive_{i_type} | Content: {i_id}")
                            
                            from app.handlers import product_handlers
                            await product_handlers.route_interactive(sender, interactive_payload)
    except Exception as e:
        logger.error(f"Error traversing webhook payload: {e}")

async def route_message(sender: str, text: str):
    """NLP and Routing hub."""
    text_lower = text.lower()
    
    # 1. Determine Intent
    wants_catalog = any(word in text_lower for word in KEYWORDS)
    
    if wants_catalog:
        logger.info("Intent: CATALOG (confidence: 1.0)")
        # Fetch up to 10 products due to Meta API constraints
        products = await catalog_client.fetch_menu(vendor_id=VENDOR_ID)
        await whatsapp_client.send_interactive_list(sender, products)
    else:
        logger.info("Intent: BASIC_ECHO (confidence: 1.0)")
        await whatsapp_client.send_text(sender, f"You said: {text}")

import os
import json
import asyncio
import logging
from redis import asyncio as aioredis
from app import whatsapp_client, catalog_client, session_manager
from app.handlers import cart_handlers, checkout_handlers
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
    
    # 0. Global Navigational Intent Determinations
    # We map keywords BEFORE enforcing session lockouts, effectively allowing
    # a user to escape a conversational loop if they type "menu" or "cart" halfway through checkout.
    wants_catalog = any(word in text_lower for word in KEYWORDS)
    wants_cart = any(word in text_lower for word in {"cart", "basket", "view cart"})
    wants_checkout = any(word in text_lower for word in {"checkout", "place order", "buy", "buy now"})
    wants_cancel = "cancel" in text_lower
    
    state = await session_manager.get_state(sender)
    
    if state and (wants_catalog or wants_cart or wants_checkout or wants_cancel):
        # The user typed a primary navigation keyword. Let them break out.
        await session_manager.clear_state(sender)
        state = {} # wipe local evaluation object
        
    if state:
        s_type = state.get("state")
        metadata = state.get("metadata", {})
        if s_type == "AWAITING_QUANTITY":
            await cart_handlers.handle_quantity_input(sender, text, metadata)
            return
        elif s_type == "AWAITING_ADDRESS":
            await checkout_handlers.handle_address_input(sender, text)
            return
    
    # 1. Active Routing
    if wants_checkout:
        logger.info("Intent: CHECKOUT (confidence: 1.0)")
        await checkout_handlers.initiate_checkout(sender)
    elif wants_cart:
        logger.info("Intent: VIEW_CART (confidence: 1.0)")
        await cart_handlers.handle_view_cart(sender)
    elif wants_catalog:
        logger.info("Intent: CATALOG (confidence: 1.0)")
        products = await catalog_client.fetch_menu(vendor_id=VENDOR_ID)
        await whatsapp_client.send_interactive_list(sender, products)
    elif wants_cancel:
        logger.info("Intent: CANCEL (confidence: 1.0)")
        await whatsapp_client.send_text(sender, "Cancelled action. Type 'menu' whenever you are ready.")
    else:
        logger.info("Intent: UNKNOWN (confidence: 1.0)")
        await whatsapp_client.send_text(sender, "I'm sorry, I don't understand that command. Type 'menu' or 'catalog' to browse our store!")

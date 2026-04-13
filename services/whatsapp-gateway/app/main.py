import json
import logging
import os

import httpx
import redis.asyncio as aioredis
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, Response

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
VERIFY_TOKEN: str = os.getenv("VERIFY_TOKEN", "")
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_CHANNEL: str = "raw_whatsapp_messages"
WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID: str = os.getenv("PHONE_NUMBER_ID", "")

# ---------------------------------------------------------------------------
# App + Redis
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PromptCart WhatsApp Gateway",
    description=(
        "Microservice 1/9 — Receives WhatsApp webhooks and publishes "
        "raw payloads to Redis Pub/Sub. No business logic."
    ),
    version="0.1.0",
)

logger = logging.getLogger("whatsapp_gateway")
logging.basicConfig(level=logging.INFO)

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return (and lazily create) the shared async Redis connection."""
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


async def send_whatsapp_message(to: str, text: str) -> None:
    """Sends a text message back to the user via the Meta WhatsApp system."""
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials missing. Skipping echo send.")
        return

    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            logger.info("Successfully sent WhatsApp message to %s", to)
    except Exception as e:
        logger.error("Failed to send WhatsApp message to %s: %s", to, e)



@app.get(
    "/webhook",
    summary="WhatsApp hub challenge verification",
    response_class=Response,
)
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> Response:
    """
    WhatsApp calls this endpoint to verify ownership of the webhook URL.
    Responds with the hub.challenge value when token matches.
    """
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning(
        "Webhook verification failed. mode=%s token_match=%s",
        hub_mode,
        hub_verify_token == VERIFY_TOKEN,
    )
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post(
    "/webhook",
    summary="Receive inbound WhatsApp messages",
)
async def receive_message(request: Request) -> dict:
    """
    Receives the raw WhatsApp message payload.
    Immediately publishes it to Redis Pub/Sub on channel `raw_whatsapp_messages`.
    Returns 200 OK with no downstream calls.
    """
    body = await request.body()
    payload_str = body.decode("utf-8")

    try:
        # Validate it's parseable JSON (WhatsApp always sends JSON)
        payload_data = json.loads(payload_str)
    except json.JSONDecodeError:
        logger.error("Received non-JSON payload, rejecting.")
        raise HTTPException(status_code=400, detail="Payload must be valid JSON")

    redis = await get_redis()
    await redis.publish(REDIS_CHANNEL, payload_str)
    logger.info("Published message to Redis channel '%s'", REDIS_CHANNEL)

    # Defensively parse the payload to extract the message text and sender
    try:
        entries = payload_data.get("entry", [])
        if entries:
            changes = entries[0].get("changes", [])
            if changes:
                value = changes[0].get("value", {})
                messages = value.get("messages", [])
                if messages:
                    msg = messages[0]
                    sender_phone = msg.get("from")
                    text_body = msg.get("text", {}).get("body")

                    if sender_phone and text_body:
                        # Echo the message back to the sender safely in the background, or inline but not blocking the 200 OK
                        await send_whatsapp_message(sender_phone, f"Echo: {text_body}")
    except Exception as e:
        # Never crash the webhook processing if extraction/echo logic fails
        logger.error("Error occurred while attempting to echo message: %s", e)

    return {"status": "received"}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok", "service": "whatsapp-gateway"}

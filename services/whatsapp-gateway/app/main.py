import json
import logging
import os

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
        json.loads(payload_str)
    except json.JSONDecodeError:
        logger.error("Received non-JSON payload, rejecting.")
        raise HTTPException(status_code=400, detail="Payload must be valid JSON")

    redis = await get_redis()
    await redis.publish(REDIS_CHANNEL, payload_str)

    logger.info("Published message to Redis channel '%s'", REDIS_CHANNEL)
    return {"status": "received"}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok", "service": "whatsapp-gateway"}

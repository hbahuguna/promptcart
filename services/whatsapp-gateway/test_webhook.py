"""
test_webhook.py
Unit tests for the WhatsApp Gateway Service.

No external services needed — Redis is mocked.
Run with:  pytest test_webhook.py -v
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Patch VERIFY_TOKEN before the app module is imported so the env var is set.
import os
os.environ.setdefault("VERIFY_TOKEN", "test_verify_token")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

from app.main import app, REDIS_CHANNEL  # noqa: E402


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────


@pytest.fixture
def mock_redis():
    """Return an async mock that replaces the real Redis client."""
    redis_mock = AsyncMock()
    redis_mock.publish = AsyncMock(return_value=1)
    return redis_mock


@pytest_asyncio.fixture
async def client(mock_redis):
    """AsyncClient backed directly by the ASGI app (no network)."""
    with patch("app.main.get_redis", return_value=mock_redis):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac, mock_redis


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_challenge_response(client):
    """GET /webhook with valid token returns hub.challenge as plain text."""
    ac, _ = client
    response = await ac.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test_verify_token",
            "hub.challenge": "abc123",
        },
    )
    assert response.status_code == 200
    assert response.text == "abc123"


@pytest.mark.asyncio
async def test_invalid_token_rejected(client):
    """GET /webhook with wrong token returns 403."""
    ac, _ = client
    response = await ac.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "WRONG_TOKEN",
            "hub.challenge": "abc123",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_wrong_mode_rejected(client):
    """GET /webhook with mode != 'subscribe' returns 403."""
    ac, _ = client
    response = await ac.get(
        "/webhook",
        params={
            "hub.mode": "unsubscribe",
            "hub.verify_token": "test_verify_token",
            "hub.challenge": "abc123",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_post_message_publishes_to_redis(client):
    """POST /webhook publishes the raw JSON to Redis and returns 200."""
    ac, redis_mock = client
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "12345",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [{"from": "911234567890", "text": {"body": "Hi!"}}],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    response = await ac.post(
        "/webhook",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "received"}

    # Verify Redis publish was called once with the correct channel and payload
    redis_mock.publish.assert_called_once()
    call_args = redis_mock.publish.call_args
    assert call_args[0][0] == REDIS_CHANNEL
    published = json.loads(call_args[0][1])
    assert published["object"] == "whatsapp_business_account"


@pytest.mark.asyncio
async def test_post_invalid_json_rejected(client):
    """POST /webhook with non-JSON body returns 400."""
    ac, _ = client
    response = await ac.post(
        "/webhook",
        content=b"not-json-at-all",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """GET /health returns 200 with status ok."""
    ac, _ = client
    response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

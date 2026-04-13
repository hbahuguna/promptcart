"""
test_webhook.py
Unit tests for the WhatsApp Gateway Service.

No external services needed — Redis is mocked.
Run with:  pytest test_webhook.py -v
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Patch VERIFY_TOKEN before the app module is imported so the env var is set.
import os
os.environ.setdefault("VERIFY_TOKEN", "test_verify_token")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("WHATSAPP_TOKEN", "test_whatsapp_token")
os.environ.setdefault("PHONE_NUMBER_ID", "123456789")

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
@patch("app.main.httpx.AsyncClient")
async def test_post_message_publishes_to_redis(mock_async_client_class, client):
    """POST /webhook publishes the raw JSON to Redis, sends echo via Meta API, and returns 200."""
    # Setup the async HTTP client mock context manager
    mock_instance = AsyncMock()
    mock_instance.post.return_value.raise_for_status = MagicMock()
    mock_async_client_class.return_value.__aenter__.return_value = mock_instance

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

    # Verify Meta API was called for the echo
    mock_instance.post.assert_called_once()
    post_args = mock_instance.post.call_args
    assert post_args[0][0] == "https://graph.facebook.com/v22.0/123456789/messages"
    assert post_args[1]["headers"]["Authorization"] == "Bearer test_whatsapp_token"
    assert post_args[1]["json"]["to"] == "911234567890"
    assert post_args[1]["json"]["text"]["body"] == "Echo: Hi!"


@pytest.mark.asyncio
@patch("app.main.httpx.AsyncClient")
async def test_post_message_echo_failure_still_returns_200(mock_async_client_class, client):
    """If the Meta API fails during the echo, the webhook still safely returns 200."""
    mock_instance = AsyncMock()
    # Simulate an HTTP error raised by a synchronous raise_for_status() on the Response object
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("HTTP 500 error")
    mock_instance.post.return_value = mock_response
    mock_async_client_class.return_value.__aenter__.return_value = mock_instance

    ac, _ = client
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "12345",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [{"from": "911234567890", "text": {"body": "Fail test!"}}],
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

    # Must still be 200 OK
    assert response.status_code == 200
    assert response.json() == {"status": "received"}


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

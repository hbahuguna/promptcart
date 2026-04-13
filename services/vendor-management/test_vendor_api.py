"""
Pytest integration tests for Vendor Management Service.
This uses an in-memory SQLite database mapped to async SQLAlchemy.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Re-route the database to SQLite memory before starting the app imports
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.database import Base, engine, get_db
from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def init_db():
    """Create fresh tables in the in-memory SQLite db for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client():
    """Returns an async HTTP client attached to the FastAPI ASGI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_vendor(client: AsyncClient):
    payload = {
        "name": "Super Fast Mart",
        "type": "DARK_STORE",
        "phone_number": "919999999999",
        "address": "123 Main St",
    }
    resp = await client.post("/api/v1/vendors/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Super Fast Mart"
    assert data["type"] == "DARK_STORE"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_get_vendor(client: AsyncClient):
    # First create
    create_resp = await client.post(
        "/api/v1/vendors/",
        json={
            "name": "Quick Corner",
            "type": "SHOPKEEPER",
            "phone_number": "918888888888",
        },
    )
    v_id = create_resp.json()["id"]

    # Then retrieve
    get_resp = await client.get(f"/api/v1/vendors/{v_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Quick Corner"


@pytest.mark.asyncio
async def test_list_vendors(client: AsyncClient):
    await client.post(
        "/api/v1/vendors/",
        json={"name": "V1", "type": "DARK_STORE", "phone_number": "1"},
    )
    await client.post(
        "/api/v1/vendors/",
        json={"name": "V2", "type": "SHOPKEEPER", "phone_number": "2"},
    )

    list_resp = await client.get("/api/v1/vendors/")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2

    # Test filtering
    filter_resp = await client.get("/api/v1/vendors/?type=DARK_STORE")
    assert filter_resp.status_code == 200
    data = filter_resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "V1"


@pytest.mark.asyncio
async def test_soft_delete_vendor(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/vendors/",
        json={"name": "Delete Me", "type": "SHOPKEEPER", "phone_number": "3"},
    )
    v_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/vendors/{v_id}")
    assert delete_resp.status_code == 204

    # Verify field was toggled
    get_resp = await client.get(f"/api/v1/vendors/{v_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_update_vendor(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/vendors/",
        json={"name": "Update Me", "type": "SHOPKEEPER", "phone_number": "4"},
    )
    v_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/vendors/{v_id}",
        json={"type": "DARK_STORE"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["type"] == "DARK_STORE"

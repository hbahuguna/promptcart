"""
Pytest integration tests for Catalog Service.
Uses in-memory SQLite overridden via setenv.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Re-route the database to SQLite memory before setting up app
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
async def test_create_product(client: AsyncClient):
    payload = {
        "vendor_id": "v123",
        "name": "Coca Cola 500ml",
        "price": "1.50",
        "category": "Beverages",
    }
    resp = await client.post("/api/v1/products", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Coca Cola 500ml"
    assert data["price"] == "1.50"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_get_product(client: AsyncClient):
    payload = {
        "vendor_id": "v123",
        "name": "Potato Chips",
        "price": "2.99",
        "category": "Snacks",
    }
    create_resp = await client.post("/api/v1/products", json=payload)
    p_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/products/{p_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Potato Chips"


@pytest.mark.asyncio
async def test_list_products_with_pagination_and_filters(client: AsyncClient):
    # Create 3 products. 1 inactive.
    await client.post("/api/v1/products", json={"vendor_id": "v1", "name": "P1", "price": "1", "category": "C1"})
    await client.post("/api/v1/products", json={"vendor_id": "v1", "name": "P2", "price": "2", "category": "C2"})
    inactive = await client.post("/api/v1/products", json={"vendor_id": "v2", "name": "P3", "price": "3", "category": "C1"})
    
    # Soft delete the third one
    await client.delete(f"/api/v1/products/{inactive.json()['id']}")

    # 1. Base list (Active only)
    resp1 = await client.get("/api/v1/products")
    assert len(resp1.json()) == 2

    # 2. List with inactive
    resp2 = await client.get("/api/v1/products?include_inactive=true")
    assert len(resp2.json()) == 3

    # 3. Filter by category
    resp3 = await client.get("/api/v1/products?category=C1")
    assert len(resp3.json()) == 1

    # 4. Filter by vendor
    resp4 = await client.get("/api/v1/products/vendor/v1")
    assert len(resp4.json()) == 2

    # 5. Pagination
    resp5 = await client.get("/api/v1/products?limit=1")
    assert len(resp5.json()) == 1


@pytest.mark.asyncio
async def test_soft_delete_product(client: AsyncClient):
    payload = {
        "vendor_id": "v9",
        "name": "Delete Me",
        "price": "0.99",
        "category": "Trash",
    }
    create_resp = await client.post("/api/v1/products", json=payload)
    p_id = create_resp.json()["id"]

    # Delete
    delete_resp = await client.delete(f"/api/v1/products/{p_id}")
    assert delete_resp.status_code == 204

    # Get should 404
    get_resp = await client.get(f"/api/v1/products/{p_id}")
    assert get_resp.status_code == 404

    # Get with include_inactive=true should 200
    get_inactive = await client.get(f"/api/v1/products/{p_id}?include_inactive=true")
    assert get_inactive.status_code == 200
    assert get_inactive.json()["is_active"] is False


@pytest.mark.asyncio
async def test_update_product(client: AsyncClient):
    payload = {
        "vendor_id": "v9",
        "name": "Update Me",
        "price": "1.00",
        "category": "Update",
    }
    create_resp = await client.post("/api/v1/products", json=payload)
    p_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/products/{p_id}",
        json={"price": "5.00"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["price"] == "5.00"

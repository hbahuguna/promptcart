import pytest
from httpx import AsyncClient, ASGITransport
import uuid
from decimal import Decimal
from unittest.mock import patch, AsyncMock
from app.main import app

def test_decimal_encoder():
    from app.events import DecimalEncoder
    import json
    v = json.dumps({"d": Decimal("10.5")}, cls=DecimalEncoder)
    assert v == '{"d": 10.5}'

@pytest.mark.asyncio
async def test_order_creation_flow():
    # Setup test DB or bypass via Mocking the router logic directly.
    # We will simulate the HTTP route via TestClient to verify pydantic bounds.
    mock_payload = {
        "customer_whatsapp_number": "+1234567890",
        "vendor_id": str(uuid.uuid4()),
        "total_amount": "50.00",
        "delivery_address": "Name: User\nHouse: 12\nMohalla: Sample\nLandmark: Tree\n(GPS: 0.1, 0.2)",
        "items": [
             {
                 "product_id": str(uuid.uuid4()),
                 "product_name": "Test Chips",
                 "quantity": 2,
                 "unit_price": "25.00",
                 "total_price": "50.00"
             }
        ]
    }
    
    with patch("app.events.publish_order_created", new_callable=AsyncMock) as mocked_publish:
        # Since database logic binds to AsyncPG we'll mock the dependency or spin up SQLite in-memory
        from app.database import get_db
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from app.database import Base
        
        test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)
        
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        async def override_get_db():
            async with TestSessionLocal() as session:
                yield session
                
        app.dependency_overrides[get_db] = override_get_db
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/v1/orders", json=mock_payload)
            
        assert res.status_code == 200
        data = res.json()
        assert data["customer_whatsapp_number"] == "+1234567890"
        assert len(data["items"]) == 1
        
        # Verify redis publisher was called natively!
        mocked_publish.assert_called_once()

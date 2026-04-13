import pytest
from unittest.mock import patch, ANY
from decimal import Decimal

from app.cart_service import get_cart_summary
from app.redis_listener import route_message

@pytest.fixture
def sample_cart():
    # raw cart returned directly from redis hgetall strings
    return {"prod_1": "2", "prod_2": "1"}

@pytest.fixture
def mock_catalog():
    def _mock_catalog(product_id: str):
        if product_id == "prod_1":
            return {"id": "prod_1", "name": "Apple", "price": "100.5"}
        elif product_id == "prod_2":
            return {"id": "prod_2", "name": "Banana", "price": "50.75"}
        return None
    return _mock_catalog

@pytest.mark.asyncio
async def test_get_cart_summary_aggregates_decimal_precision(sample_cart, mock_catalog):
    """
    Test that Decimals properly sum avoiding precision errors.
    2 * 100.5 = 201.0
    1 * 50.75 = 50.75
    Total = 251.75
    """
    with patch("app.cart_service.get_cart") as mock_get_cart:
        with patch("app.catalog_client.get_product_by_id", side_effect=mock_catalog):
            mock_get_cart.return_value = sample_cart
            
            summary = await get_cart_summary("999")
            
            assert len(summary["items"]) == 2
            assert summary["total_price"] == Decimal("251.75")
            assert summary["items"][0]["line_total"] == Decimal("201.00")

@pytest.mark.asyncio
async def test_session_lockout_intercepts_regular_keywords():
    """
    Ensures that when AWAITING_QUANTITY is active, a user typing "menu" 
    clears the session lock natively and invokes the catalog fallback.
    """
    mock_state = {
        "state": "AWAITING_QUANTITY",
        "metadata": {"product_id": "prod_1"}
    }
    
    with patch("app.redis_listener.session_manager.get_state", return_value=mock_state):
        with patch("app.redis_listener.session_manager.clear_state") as mock_clear:
            with patch("app.redis_listener.cart_handlers.handle_quantity_input") as mock_qty:
                with patch("app.redis_listener.catalog_client.fetch_menu") as mock_catalog:
                    
                    # Should route to catalog seamlessly exiting quantity constraints
                    await route_message("999", "menu")
                    
                    mock_qty.assert_not_called()
                    mock_catalog.assert_called_once()
                    mock_clear.assert_called_once_with("999")

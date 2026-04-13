import pytest
from unittest.mock import patch, ANY

from app.redis_listener import process_webhook
from app.handlers.product_handlers import route_interactive, handle_product_selection, handle_button_reply

def create_list_reply_payload(sender: str, item_id: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "value": {
                    "messages": [{
                        "from": sender,
                        "type": "interactive",
                        "interactive": {
                            "type": "list_reply",
                            "list_reply": {"id": item_id}
                        }
                    }]
                }
            }]
        }]
    }

def create_button_reply_payload(sender: str, button_id: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "value": {
                    "messages": [{
                        "from": sender,
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {"id": button_id}
                        }
                    }]
                }
            }]
        }]
    }

@pytest.fixture
def sample_product():
    return {
        "id": "prod_123",
        "name": "Coca Cola",
        "description": "500ml bottle",
        "price": "40.00"
    }

@pytest.mark.asyncio
async def test_interactive_list_reply_triggers_product_selection():
    """
    Test deep parsing of `list_reply`. Ensures we hit routing engine accurately.
    """
    payload = create_list_reply_payload("999", "prod_123")
    
    with patch("app.handlers.product_handlers.handle_product_selection") as mock_selection:
        await process_webhook(payload)
        
        mock_selection.assert_called_once_with("999", "prod_123")


@pytest.mark.asyncio
async def test_handle_product_selection(sample_product):
    """
    Ensure selecting a list replies back with Catalog HTTP request and WhatsApp UI Buttons.
    """
    with patch("app.handlers.product_handlers.catalog_client.get_product_by_id") as mock_get:
        with patch("app.handlers.product_handlers.whatsapp_client.send_interactive_buttons") as mock_send:
            mock_get.return_value = sample_product
            
            await handle_product_selection("999", "prod_123")
            
            mock_get.assert_called_once_with("prod_123")
            mock_send.assert_called_once()
            
            kwargs = mock_send.call_args[1]
            assert "to" in kwargs
            assert "header" in kwargs
            assert kwargs["header"] == "Coca Cola"


@pytest.mark.asyncio
async def test_interactive_button_reply_triggers_button_logic():
    """
    Test deep parsing of `button_reply`. Ensures we hit routing engine accurately.
    """
    payload = create_button_reply_payload("999", "add_to_cart:prod_123")
    
    with patch("app.handlers.product_handlers.handle_button_reply") as mock_button:
        await process_webhook(payload)
        
        mock_button.assert_called_once_with("999", "add_to_cart:prod_123")


@pytest.mark.asyncio
async def test_handle_add_to_cart_via_button(sample_product):
    """
    Test cart assignment to Redis instance natively via the button interceptor.
    """
    with patch("app.handlers.product_handlers.catalog_client.get_product_by_id") as mock_get:
        with patch("app.handlers.product_handlers.cart_service.add_to_cart") as mock_add:
            with patch("app.handlers.product_handlers.whatsapp_client.send_text") as mock_send:
                mock_get.return_value = sample_product
                
                await handle_button_reply("999", "add_to_cart:prod_123")
                
                mock_get.assert_called_once_with("prod_123")
                mock_add.assert_called_once_with(whatsapp_number="999", product_id="prod_123", qty=1)
                
                # Check for success message execution
                mock_send.assert_called_once()
                body = mock_send.call_args[0][1]
                assert "Coca Cola" in body
                assert "cart" in body.lower()

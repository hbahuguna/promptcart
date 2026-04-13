import pytest
from unittest.mock import patch, ANY
import json

from app.redis_listener import process_webhook, route_message

def create_webhook_payload(sender: str, text: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": sender,
                                    "id": "wamid.XYZ",
                                    "timestamp": "1710000000",
                                    "type": "text",
                                    "text": {"body": text}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

@pytest.fixture
def sample_catalog_response():
    return [
        {
            "id": "prod_1",
            "name": "Coca Cola 500ml",
            "description": "Cold beverage",
            "price": "40.00",
        },
        {
            "id": "prod_2",
            "name": "Lays Classic",
            "description": "Chips",
            "price": "20.00",
        }
    ]

@pytest.mark.asyncio
async def test_route_message_catalog_intent(sample_catalog_response):
    """
    Test that sending 'menu' triggers the Catalog API and fires a formatting Interactive List message.
    """
    sender = "1234567890"
    
    with patch("app.redis_listener.catalog_client.fetch_menu") as mock_fetch:
        with patch("app.redis_listener.whatsapp_client.send_interactive_list") as mock_send:
            mock_fetch.return_value = sample_catalog_response
            
            # Action
            await route_message(sender, "show me the menu please")
            
            # Assertions
            mock_fetch.assert_called_once_with(vendor_id=ANY)
            mock_send.assert_called_once_with(sender, sample_catalog_response)

@pytest.mark.asyncio
async def test_route_message_echo_fallback():
    """
    Test that random gibberish defaults to standard Echo text messages.
    """
    sender = "1234567890"
    
    with patch("app.redis_listener.catalog_client.fetch_menu") as mock_fetch:
        with patch("app.redis_listener.whatsapp_client.send_text") as mock_send_text:
            
            # Action
            await route_message(sender, "hello how are you")
            
            # Assertions
            mock_fetch.assert_not_called()
            mock_send_text.assert_called_once_with(sender, "You said: hello how are you")

@pytest.mark.asyncio
async def test_process_webhook_extraction():
    """
    Verify that our parsing engine properly unwraps deep Meta payloads and ships them to route_message.
    """
    payload = create_webhook_payload("999", "products")
    
    with patch("app.redis_listener.route_message") as mock_route:
        await process_webhook(payload)
        
        mock_route.assert_called_once_with("999", "products")

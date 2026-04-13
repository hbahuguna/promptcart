import pytest
import json
from unittest.mock import patch, ANY

from app.logger_utils import mask_phone
from app.redis_listener import process_webhook

def test_mask_phone_truncates_pii():
    """Verify core privacy compliance string obfuscation defaults."""
    assert mask_phone("1234567890") == "123****90"
    assert mask_phone("12345") == "****"
    assert mask_phone("") == "UNKNOWN"

@pytest.mark.asyncio
async def test_inbound_interaction_logs_safely(caplog):
    """
    Simulates webhook interception asserting standard inbound message details are recorded into CapLog
    completely devoid of phone numbers or raw identifiers.
    """
    dummy_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "9876543210",
                        "type": "text",
                        "text": {"body": "hello show me the menu"}
                    }]
                }
            }]
        }]
    }

    # Lock downstream calls so we are strictly observing logging operations
    with patch("app.redis_listener.catalog_client.fetch_menu"):
        with patch("app.redis_listener.whatsapp_client.send_interactive_list"):
            await process_webhook(dummy_payload)
            
    log_text = caplog.text
    
    assert "From: 987****10" in log_text, "Failure isolating PII! Raw data detected."
    assert "9876543210" not in log_text, "Strict strict privacy verification failed"
    assert "Type: text" in log_text
    assert "Intent: CATALOG" in log_text

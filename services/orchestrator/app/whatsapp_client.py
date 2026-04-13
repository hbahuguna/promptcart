import os
import httpx
import logging

logger = logging.getLogger("orchestrator_whatsapp")

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

def get_base_url() -> str:
    return f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

async def send_text(to: str, message: str) -> bool:
    """Send a standard text message."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    return await _post_to_whatsapp(payload)

async def send_interactive_list(to: str, products: list) -> bool:
    """Send an interactive list message. Max 10 items per section per WhatsApp spec."""
    if not products:
        return await send_text(to, "Sorry, this vendor currently has no products available.")

    # Slice to top 10 items to strictly enforce Meta's maximum limit for a single interactive list section
    limited_products = products[:10]
    
    rows = []
    for p in limited_products:
        # Title limit is 24 chars, Description is 72 chars
        title = p["name"][:24]
        price = float(p["price"])
        desc = f"₹{price:.2f}"
        if p.get("description"):
            desc += f" - {p['description']}"
            
        rows.append({
            "id": p["id"][:200], # Max 200 chars
            "title": title,
            "description": desc[:72]
        })

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "Our Products"
            },
            "body": {
                "text": "Here are some items you might like:"
            },
            "footer": {
                "text": "Tap an item to view details"
            },
            "action": {
                "button": "View Items",
                "sections": [
                    {
                        "title": "Available Products",
                        "rows": rows
                    }
                ]
            }
        }
    }
    
    return await _post_to_whatsapp(payload)

async def _post_to_whatsapp(payload: dict) -> bool:
    """Internal helper to dispatch to Meta API."""
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials missing. Skipping Meta API call.")
        return False
        
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(get_base_url(), json=payload, headers=get_headers())
            resp.raise_for_status()
            logger.info(f"WhatsApp message sent to {payload.get('to')}")
            return True
            
    except httpx.HTTPStatusError as e:
        logger.error(f"WhatsApp API HTTP Error: {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"WhatsApp API Error: {e}")
        return False

import json
import logging
from app.cart_service import _redis_pool

logger = logging.getLogger("orchestrator_session")

def _get_session_key(whatsapp_number: str) -> str:
    return f"session:{whatsapp_number}"

async def set_state(whatsapp_number: str, state_type: str, metadata: dict = None):
    """
    Persist conversational state tracking with an arbitrary data blob.
    Expires globally after 10 minutes to auto-reset stuck shopping cart sessions.
    """
    key = _get_session_key(whatsapp_number)
    payload = {
        "state": state_type,
        "metadata": metadata or {}
    }
    
    try:
        # Store serialized JSON string with 600 second TTL (10 minutes)
        await _redis_pool.setex(key, 600, json.dumps(payload))
        logger.info(f"Session State {state_type} locked for {whatsapp_number}")
    except Exception as e:
        logger.error(f"Failed to set session state {state_type}: {e}")

async def get_state(whatsapp_number: str) -> dict:
    """
    Retrieve user state block structure mapping to dict.
    Returns empty dictionary if no active session is enforced.
    """
    key = _get_session_key(whatsapp_number)
    try:
        raw = await _redis_pool.get(key)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.error(f"Failed to get session state: {e}")
        
    return {}

async def clear_state(whatsapp_number: str):
    """
    Manually removes conversational lockouts, resuming normal NLP routing.
    """
    key = _get_session_key(whatsapp_number)
    try:
        await _redis_pool.delete(key)
        logger.info(f"Cleared Session Locks for {whatsapp_number}")
    except Exception as e:
        logger.error(f"Failed to clear session state: {e}")

import httpx
from app.logger_utils import setup_logger

logger = setup_logger("orchestrator_customer")
# Note: Since the Customer microservice does not exist yet (stub mapped for Phase 5)
# we are hard-mocking the local return value for now.
_mock_customers = {}

async def get_customer(whatsapp_number: str) -> dict:
    """
    Checks if a user has registered details from the mock database.
    """
    logger.info(f"Checked API for customer profile {whatsapp_number}")
    return _mock_customers.get(whatsapp_number, {})

async def save_address(whatsapp_number: str, address: str) -> bool:
    """
    Saves an inbound address against the user account profile.
    """
    if whatsapp_number not in _mock_customers:
        _mock_customers[whatsapp_number] = {}
    _mock_customers[whatsapp_number]["address"] = address
    logger.info(f"Mocked HTTP saving profile address to {whatsapp_number}")
    return True

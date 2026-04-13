import httpx
from app.logger_utils import setup_logger

logger = setup_logger("orchestrator_customer")
# Note: Since the Customer microservice does not exist yet (stub mapped for Phase 5)
# we are hard-mocking the local return value for now.

async def get_customer(whatsapp_number: str) -> dict:
    """
    Checks if a user has registered details. Mock returning none currently 
    to trigger the User Onboarding "Provide Address" flow natively.
    """
    logger.info(f"Checked API for customer profile {whatsapp_number}")
    return {} # Force "no address" flow

async def save_address(whatsapp_number: str, address: str) -> bool:
    """
    Saves an inbound address against the user account profile.
    Mocking true successfully.
    """
    logger.info(f"Mocked HTTP saving profile address {address} to {whatsapp_number}")
    return True

import os
import httpx
import logging

logger = logging.getLogger("orchestrator_catalog")

CATALOG_URL = os.environ.get("CATALOG_SERVICE_URL", "http://localhost:8002")

async def fetch_menu(vendor_id: str) -> list:
    """
    Fetches the first 10 products for a vendor from the Catalog service.
    """
    url = f"{CATALOG_URL}/api/v1/products"
    params = {
        "vendor_id": vendor_id,
        "limit": 10
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch menu for vendor {vendor_id}: {e}")
        return []

async def get_product_by_id(product_id: str) -> dict:
    """
    Fetch comprehensive product details via Product UUID.
    """
    url = f"{CATALOG_URL}/api/v1/products/{product_id}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Catalog Product Lookup HTTP Error: {e.response.status_code}")
        return {}
    except Exception as e:
        logger.error(f"Failed to fetch product {product_id}: {e}")
        return {}

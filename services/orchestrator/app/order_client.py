import os
import httpx
from app.logger_utils import setup_logger

logger = setup_logger("orchestrator_order")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order-api:8004")

async def create_order(whatsapp_number: str, vendor_id: str, items: list, delivery_address: str, total_amount: float) -> dict:
    url = f"{ORDER_SERVICE_URL}/api/v1/orders"
    payload = {
        "customer_whatsapp_number": whatsapp_number,
        "vendor_id": vendor_id,
        "total_amount": float(total_amount),
        "delivery_address": delivery_address,
        "items": []
    }
    for i in items:
        payload["items"].append({
            "product_id": i["product_id"],
            "product_name": i["name"],
            "quantity": int(i["quantity"]),
            "unit_price": float(i["price"]),
            "total_price": float(i["price"]) * float(i["quantity"])
        })
        
    async with httpx.AsyncClient() as client:
        logger.info(f"POST {url} creating remote exact order schema map...")
        res = await client.post(url, json=payload)
        res.raise_for_status()
        return res.json()

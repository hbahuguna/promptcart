import logging
from app import whatsapp_client, cart_service, customer_client, session_manager

logger = logging.getLogger("orchestrator_checkout")

async def initiate_checkout(sender: str):
    """
    Verifies that a cart exists, and proceeds to poll customer systems for valid profiles.
    """
    summary = await cart_service.get_cart_summary(sender)
    
    if not summary["items"]:
        await whatsapp_client.send_text(sender, "🛒 Your cart is empty. Type 'menu' to browse our catalogue before checking out.")
        return
        
    customer = await customer_client.get_customer(sender)
    address = customer.get("address")
    
    total_str = f"₹{summary['total_price']:.2f}"
    
    if address:
        body = f"📦 *Order Summary*\nTotal: {total_str}\nDeliver To: {address}\n\nPlease confirm your order!"
        buttons = [
            {"id": "confirm_order", "title": "Confirm Order"},
            {"id": "change_address", "title": "Change Address"},
            {"id": "view_cart", "title": "Cancel"}
        ]
        await whatsapp_client.send_interactive_buttons(sender, "Checkout", body, buttons)
    else:
        # State machine interception required!
        await session_manager.set_state(sender, "AWAITING_ADDRESS_GPS")
        await whatsapp_client.send_location_request(sender, "📍 We need your delivery address!\nPlease share your precise GPS location below:")

async def handle_gps_location(sender: str, lat: float, lng: float):
    """
    Receives physical coordinate structure, saving into temporal state.
    """
    await session_manager.set_state(sender, "AWAITING_ADDRESS_DETAILS", {"lat": lat, "lng": lng})
    await whatsapp_client.send_text(sender, "✅ Location saved!\nNow, please reply with your *House/Flat No. and Landmark* (e.g. 'Flat 4B, Sector 5').")

async def handle_address_details_input(sender: str, text: str, metadata: dict):
    """
    Captures text appending it into the active geographical anchor, creating a formatted structure.
    """
    if len(text) < 3:
        await whatsapp_client.send_text(sender, "Please provide a valid House/Flat No. and Landmark details.")
        return
        
    lat = metadata.get("lat")
    lng = metadata.get("lng")
    structured_address = f"{text} (GPS: {lat}, {lng})"
    
    await customer_client.save_address(sender, structured_address)
    await session_manager.clear_state(sender)
    
    await whatsapp_client.send_text(sender, "✅ Structured Address saved successfully!")
    await initiate_checkout(sender)

async def handle_order_confirmation(sender: str):
    """
    Stubs the order placed Redis Pub/Sub integration required for Phase 5.
    """
    import os
    import json
    from app.cart_service import _redis_pool
    
    summary = await cart_service.get_cart_summary(sender)
    customer = await customer_client.get_customer(sender)
    
    order_payload = {
        "whatsapp_number": sender,
        "items": summary["items"],
        "total_amount": float(summary["total_price"]),
        "address": customer.get("address", "UNKNOWN")
    }
    
    # Broadcast to Phase 5 system pipeline
    await _redis_pool.publish("order_placed", json.dumps(order_payload))
    await cart_service.clear_cart(sender)
    
    await whatsapp_client.send_text(sender, "🎉 *Order placed!* Your order `#ORD-12345` is being processed. We'll notify you when it's packed and on the way.")

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
    await session_manager.set_state(sender, "AWAITING_CUSTOMER_NAME", {"lat": lat, "lng": lng})
    await whatsapp_client.send_text(sender, "✅ Location saved!\n\nLet's get a few more details.\nFirst, *please reply with your Full Name*:")

async def handle_wizard_name_input(sender: str, text: str, metadata: dict):
    if len(text) < 2:
        await whatsapp_client.send_text(sender, "Please enter a valid name.")
        return
    metadata["name"] = text.strip()
    await session_manager.set_state(sender, "AWAITING_HOUSE_NUMBER", metadata)
    await whatsapp_client.send_text(sender, "Thanks! Now, *please reply with your House Name or Number*:")

async def handle_wizard_house_input(sender: str, text: str, metadata: dict):
    metadata["house"] = text.strip()
    await session_manager.set_state(sender, "AWAITING_MOHALLA", metadata)
    await whatsapp_client.send_text(sender, "Got it! Next, *what is your Mohalla/Locality/Street?*")

async def handle_wizard_mohalla_input(sender: str, text: str, metadata: dict):
    metadata["mohalla"] = text.strip()
    await session_manager.set_state(sender, "AWAITING_LANDMARK", metadata)
    await whatsapp_client.send_text(sender, "Almost done! *Finally, please reply with a nearby Landmark*:")

async def handle_wizard_landmark_input(sender: str, text: str, metadata: dict):
    """
    Final step: Captures landmark and structures the complete payload.
    """
    lat = metadata.get("lat")
    lng = metadata.get("lng")
    name = metadata.get("name")
    house = metadata.get("house")
    mohalla = metadata.get("mohalla")
    landmark = text.strip()
    
    structured_address = f"Name: {name}\nHouse: {house}\nMohalla: {mohalla}\nLandmark: {landmark}\n*(GPS: {lat}, {lng})*"
    
    await customer_client.save_address(sender, structured_address)
    await session_manager.clear_state(sender)
    
    await whatsapp_client.send_text(sender, f"✅ Structured Address saved successfully:\n\n{structured_address}")
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

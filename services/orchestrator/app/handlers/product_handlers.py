import logging

from app import whatsapp_client, catalog_client, cart_service

logger = logging.getLogger("orchestrator_handlers")

async def route_interactive(sender: str, interactive: dict):
    """
    Master router for WhatsApp Interactive payloads.
    Distinguishes List selections from Button taps.
    """
    i_type = interactive.get("type")
    
    if i_type == "list_reply":
        item_id = interactive.get("list_reply", {}).get("id")
        if item_id:
            await handle_product_selection(sender, item_id)
            
    elif i_type == "button_reply":
        button_id = interactive.get("button_reply", {}).get("id")
        if button_id:
            await handle_button_reply(sender, button_id)

async def handle_product_selection(sender: str, product_id: str):
    """
    Executes standard Flow 2: Users tap a product from the list.
    We fetch catalog details, then serve the Add To Cart button block.
    """
    product = await catalog_client.get_product_by_id(product_id)
    
    if not product:
        await whatsapp_client.send_text(sender, "Sorry, we couldn't find the details for this product.")
        return
        
    price = float(product.get("price", 0))
    header = product.get("name", "Product Details")
    desc = product.get("description", "No description available.")
    
    body = f"*Price:* ₹{price:.2f}\n*Description:* {desc}"
    
    buttons = [
        {"id": f"add_to_cart:{product_id}", "title": "Add to Cart"},
        {"id": "browse_catalog", "title": "Back to Products"}
    ]
    
    await whatsapp_client.send_interactive_buttons(
        to=sender,
        header=header[:60], # max 60 char limit
        body=body[:1024], # max 1024 char limit
        buttons=buttons
    )

async def handle_button_reply(sender: str, button_id: str):
    """
    Evaluates cart ingestion versus navigational redirects.
    """
    if button_id == "browse_catalog":
        await handle_browse_catalog(sender)
        
    elif button_id.startswith("add_to_cart:"):
        product_id = button_id.split("add_to_cart:")[1]
        await handle_add_to_cart(sender, product_id)
        
    else:
        logger.warning(f"Unrecognized interactive button reply: {button_id}")

async def handle_add_to_cart(sender: str, product_id: str):
    """
    Injects a product ID into the Redis cart pool via cart_service.
    """
    # Verify product still exists before carting it
    product = await catalog_client.get_product_by_id(product_id)
    if not product:
        await whatsapp_client.send_text(sender, "We couldn't add that to your cart. Product unavailable.")
        return
        
    await cart_service.add_to_cart(whatsapp_number=sender, product_id=product_id, qty=1)
    
    product_name = product.get("name", "Item")
    success_msg = f"✅ Added *{product_name}* to your cart!\nType 'cart' to view or 'checkout' to place order."
    await whatsapp_client.send_text(sender, success_msg)

async def handle_browse_catalog(sender: str):
    """
    Re-triggers the menu fetch.
    """
    import os
    VENDOR_ID = os.environ.get("VENDOR_ID", "bab94c54-8035-4dbd-8b9e-252e0b08d304")
    
    products = await catalog_client.fetch_menu(vendor_id=VENDOR_ID)
    await whatsapp_client.send_interactive_list(sender, products)

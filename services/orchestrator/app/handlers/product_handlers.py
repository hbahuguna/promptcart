import logging

from app import whatsapp_client, catalog_client, cart_service
from app.handlers import cart_handlers, checkout_handlers

logger = logging.getLogger("orchestrator_handlers")

async def route_interactive(sender: str, interactive: dict):
    """
    Master router for WhatsApp Interactive payloads.
    Distinguishes List selections from Button taps.
    """
    i_type = interactive.get("type")
    
    # User interacted naturally with buttons. Automatically wipe any stale session locks
    from app import session_manager
    await session_manager.clear_state(sender)
    
    if i_type == "list_reply":
        item_id = interactive.get("list_reply", {}).get("id")
        if item_id:
            if str(item_id).startswith("edit_cart_"):
                p_id = str(item_id).replace("edit_cart_", "")
                await cart_handlers.handle_edit_cart_selection(sender, p_id)
            else:
                await handle_product_selection(sender, item_id)
            
    elif i_type == "button_reply":
        button_id = interactive.get("button_reply", {}).get("id")
        if button_id:
            if button_id == "manage_cart":
                await cart_handlers.display_cart_item_options(sender)
            elif button_id == "view_cart":
                await cart_handlers.handle_view_cart(sender)
            elif button_id == "checkout_initiate":
                await checkout_handlers.initiate_checkout(sender)
            elif str(button_id).startswith("update_qty:"):
                p_id = str(button_id).split(":")[1]
                await cart_handlers.handle_update_quantity_request(sender, p_id)
            elif str(button_id).startswith("remove_item:"):
                p_id = str(button_id).split(":")[1]
                await cart_handlers.handle_remove_cart_item(sender, p_id)
            elif button_id == "confirm_order":
                await checkout_handlers.handle_order_confirmation(sender)
            elif button_id == "change_address":
                from app import session_manager
                await session_manager.set_state(sender, "AWAITING_ADDRESS")
                await whatsapp_client.send_text(sender, "📍 Please type your new full delivery address below:")
            else:
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
    
    buttons = [
        {"id": "view_cart", "title": "View Cart"},
        {"id": "checkout_initiate", "title": "Checkout"},
        {"id": "browse_catalog", "title": "Keep Shopping"}
    ]
    
    await whatsapp_client.send_interactive_buttons(
        to=sender,
        header="Added!",
        body=f"✅ Added *{product_name}* to your cart! What would you like to do next?",
        buttons=buttons
    )

async def handle_browse_catalog(sender: str):
    """
    Re-triggers the menu fetch.
    """
    import os
    VENDOR_ID = os.environ.get("VENDOR_ID", "bab94c54-8035-4dbd-8b9e-252e0b08d304")
    
    products = await catalog_client.fetch_menu(vendor_id=VENDOR_ID)
    await whatsapp_client.send_interactive_list(sender, products)

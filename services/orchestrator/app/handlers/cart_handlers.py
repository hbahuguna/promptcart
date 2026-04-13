import logging
from app import whatsapp_client, cart_service, session_manager

logger = logging.getLogger("orchestrator_cart")

async def handle_view_cart(sender: str):
    """
    Looks up the cart. If empty, warns.
    If full, sends Interactive Text buttons mapping to Checkout loops.
    """
    summary = await cart_service.get_cart_summary(sender)
    
    if not summary["items"]:
        await whatsapp_client.send_text(sender, "🛒 Your cart is currently empty. Type 'menu' to browse our catalogue!")
        return
        
    total_str = f"₹{summary['total_price']:.2f}"
    
    body = "🛒 *Your Cart Summary*\n\n"
    for idx, item in enumerate(summary["items"]):
        body += f"{idx + 1}. *{item['name']}* x{item['quantity']}\n"
        body += f"   Line Total: ₹{item['line_total']:.2f}\n"
        
    body += f"\n*Final Total: {total_str}*"
    
    buttons = [
        {"id": "checkout_initiate", "title": "Checkout"},
        {"id": "manage_cart", "title": "Manage Items"},
        {"id": "browse_catalog", "title": "Keep Shopping"}
    ]
    
    await whatsapp_client.send_interactive_buttons(
        to=sender,
        header="Review Cart",
        body=body[:1024],
        buttons=buttons
    )

async def display_cart_item_options(sender: str):
    """
    Displays the interactive list of items in the cart to modify them.
    (This kicks into the complex list routing required for modification).
    """
    summary = await cart_service.get_cart_summary(sender)
    
    if not summary["items"]:
        await whatsapp_client.send_text(sender, "Oops! Cart is empty.")
        return

    rows = []
    # Maximum 10 rows limitation per Meta API segment
    for item in summary["items"][:10]:
        rows.append({
            "id": f"edit_cart_{item['product_id']}",
            "title": f"[Edit] {item['name']}"[:24],
            "description": f"Qty: {item['quantity']} | ₹{item['line_total']:.2f}"[:72]
        })

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": sender,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Modify Items"},
            "body": {"text": "Select an item to change its quantity or remove it."},
            "action": {
                "button": "Select Item",
                "sections": [{"title": "Your Cart", "rows": rows}]
            }
        }
    }
    
    await whatsapp_client._post_to_whatsapp(payload)

async def handle_edit_cart_selection(sender: str, product_id: str):
    """
    User tapped a specific cart item to edit. Provide interactive buttons.
    """
    buttons = [
        {"id": f"update_qty:{product_id}", "title": "Change Quantity"},
        {"id": f"remove_item:{product_id}", "title": "Remove Item"},
        {"id": "view_cart", "title": "Cancel"}
    ]
    await whatsapp_client.send_interactive_buttons(
        to=sender,
        header="Modifier Options",
        body="What would you like to do with this item?",
        buttons=buttons
    )

async def handle_remove_cart_item(sender: str, product_id: str):
    """
    Removes item and bounces back to cart UI.
    """
    await cart_service.remove_item(sender, product_id)
    await whatsapp_client.send_text(sender, "🗑️ Item removed from your cart.")
    await handle_view_cart(sender)

async def handle_update_quantity_request(sender: str, product_id: str):
    """
    Locks NLP via state machine and waits for the user to type a numeric digit.
    """
    await session_manager.set_state(sender, "AWAITING_QUANTITY", {"product_id": product_id})
    await whatsapp_client.send_text(sender, "Please enter the new quantity as a number (e.g. '3'):")

async def handle_quantity_input(sender: str, text: str, metadata: dict):
    """
    Invoked when AWAITING_QUANTITY state catches normal text.
    """
    try:
        new_qty = int(text.strip())
        product_id = metadata.get("product_id")
        
        await cart_service.update_quantity(sender, product_id, new_qty)
        await session_manager.clear_state(sender)
        
        await whatsapp_client.send_text(sender, f"✅ Quantity updated to {new_qty}!")
        await handle_view_cart(sender)
        
    except ValueError:
        await whatsapp_client.send_text(sender, "That doesn't look like a valid number. Please try again (e.g. '2').")

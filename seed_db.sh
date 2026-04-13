#!/bin/bash
echo "Seeding PromptCart Databases..."

# 1. Create a Vendor (Dark Store)
echo "Creating Vendor..."
VENDOR_JSON=$(curl -s -X POST http://localhost:8001/api/v1/vendors \
  -H "Content-Type: application/json" \
  -d '{"name":"PromptCart SuperMart","type":"DARK_STORE","phone_number":"+1234567890","address":"123 Main St"}')

# Extract Vendor ID using grep and sed or node (or just prompt the user what it is if it's dynamic).
# Since jq might not be installed, we will use python to parse the JSON output
VENDOR_ID=$(python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" <<< "$VENDOR_JSON")
echo "Created Vendor ID: $VENDOR_ID"

echo "Wait 2 seconds for Catalog DB..."
sleep 2

# 2. Create products mapped to the Vendor ID
echo "Creating Products..."
curl -X POST http://localhost:8002/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_id": "'"$VENDOR_ID"'",
    "name": "Lays Classic Salted",
    "description": "Crispy potato chips",
    "price": 20.00,
    "category": "Snacks"
  }'

echo ""
curl -X POST http://localhost:8002/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_id": "'"$VENDOR_ID"'",
    "name": "Coca Cola 500ml",
    "description": "Cold beverage",
    "price": 40.00,
    "category": "Beverages"
  }'
  
echo ""
echo "Done! To verify, text 'menu' to your WhatsApp Gateway."

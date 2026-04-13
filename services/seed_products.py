#!/usr/bin/env python3
"""
Seed script to add 50 sample products to PromptCart Catalog Service.
Usage: python seed_products.py
"""

import requests
import random
import uuid
from datetime import datetime

# Configuration
CATALOG_URL = "http://localhost:8002/api/v1/products"
VENDOR_ID = "bab94c54-8035-4dbd-8b9e-252e0b08d304"

# Sample Indian grocery products with categories and price ranges
PRODUCT_TEMPLATES = [
    # Snacks
    {"name": "Lays Classic Salted", "category": "Snacks", "price": 20.00, "description": "Crispy potato chips"},
    {"name": "Lays Magic Masala", "category": "Snacks", "price": 20.00, "description": "Spicy masala flavored chips"},
    {"name": "Kurkure Masala Munch", "category": "Snacks", "price": 10.00, "description": "Crunchy corn puffs with tangy masala"},
    {"name": "Haldiram's Aloo Bhujia", "category": "Snacks", "price": 55.00, "description": "Traditional crispy potato noodles"},
    {"name": "Bingo Mad Angles", "category": "Snacks", "price": 10.00, "description": "Triangular crunchy snacks"},
    {"name": "Pringles Original", "category": "Snacks", "price": 99.00, "description": "Stackable potato crisps"},
    {"name": "Doritos Nacho Cheese", "category": "Snacks", "price": 30.00, "description": "Tortilla chips with cheese flavor"},
    {"name": "Cheetos Cheese Puffs", "category": "Snacks", "price": 20.00, "description": "Cheesy corn puffs"},
    {"name": "Parle Wafers Masala", "category": "Snacks", "price": 10.00, "description": "Classic Indian masala wafers"},
    {"name": "Too Yumm Karare", "category": "Snacks", "price": 20.00, "description": "Baked multigrain chips"},
    
    # Beverages
    {"name": "Coca-Cola 750ml", "category": "Beverages", "price": 40.00, "description": "Classic cola drink"},
    {"name": "Thums Up 750ml", "category": "Beverages", "price": 40.00, "description": "Strong cola with Indian taste"},
    {"name": "Sprite 750ml", "category": "Beverages", "price": 40.00, "description": "Lemon-lime clear soda"},
    {"name": "Fanta Orange 750ml", "category": "Beverages", "price": 40.00, "description": "Orange flavored soda"},
    {"name": "Mountain Dew 750ml", "category": "Beverages", "price": 40.00, "description": "Citrus energy drink"},
    {"name": "Red Bull 250ml", "category": "Beverages", "price": 125.00, "description": "Energy drink with caffeine"},
    {"name": "Tropicana Orange Juice 1L", "category": "Beverages", "price": 120.00, "description": "100% pure orange juice"},
    {"name": "Real Mango Juice 1L", "category": "Beverages", "price": 110.00, "description": "Mango fruit drink"},
    {"name": "Paper Boat Aam Panna 250ml", "category": "Beverages", "price": 30.00, "description": "Raw mango drink"},
    {"name": "Bisleri Mineral Water 1L", "category": "Beverages", "price": 20.00, "description": "Purified drinking water"},
    
    # Groceries
    {"name": "Tata Sampann Toor Dal 500g", "category": "Groceries", "price": 95.00, "description": "Unpolished pigeon pea lentils"},
    {"name": "Fortune Basmati Rice 1kg", "category": "Groceries", "price": 130.00, "description": "Premium long grain rice"},
    {"name": "Aashirvaad Atta 5kg", "category": "Groceries", "price": 245.00, "description": "Whole wheat flour"},
    {"name": "MDH Garam Masala 100g", "category": "Groceries", "price": 85.00, "description": "Blend of aromatic spices"},
    {"name": "Everest Turmeric Powder 200g", "category": "Groceries", "price": 65.00, "description": "Pure haldi powder"},
    {"name": "Saffola Gold Oil 1L", "category": "Groceries", "price": 175.00, "description": "Blended cooking oil"},
    {"name": "Tata Salt 1kg", "category": "Groceries", "price": 28.00, "description": "Iodized crystal salt"},
    {"name": "Maggi 2-Minute Noodles 4-Pack", "category": "Groceries", "price": 60.00, "description": "Instant noodles with masala"},
    {"name": "Kissan Tomato Ketchup 500g", "category": "Groceries", "price": 95.00, "description": "Tomato sauce condiment"},
    {"name": "Amul Butter 500g", "category": "Groceries", "price": 260.00, "description": "Pasteurized butter"},
    
    # Dairy & Eggs
    {"name": "Amul Taaza Milk 500ml", "category": "Dairy", "price": 28.00, "description": "Toned homogenized milk"},
    {"name": "Amul Cheese Slices 200g", "category": "Dairy", "price": 140.00, "description": "Processed cheese slices"},
    {"name": "Mother Dairy Paneer 200g", "category": "Dairy", "price": 85.00, "description": "Fresh cottage cheese"},
    {"name": "Amul Masti Dahi 400g", "category": "Dairy", "price": 45.00, "description": "Set curd/yogurt"},
    {"name": "Amul Malai Paneer 200g", "category": "Dairy", "price": 90.00, "description": "Creamy cottage cheese"},
    {"name": "Eggs (Pack of 6)", "category": "Dairy", "price": 54.00, "description": "Fresh table eggs"},
    {"name": "Amul Fresh Cream 250ml", "category": "Dairy", "price": 65.00, "description": "Low-fat fresh cream"},
    
    # Personal Care
    {"name": "Colgate Max Fresh Toothpaste 150g", "category": "Personal Care", "price": 95.00, "description": "Cooling gel toothpaste"},
    {"name": "Dove Soap 100g (Pack of 3)", "category": "Personal Care", "price": 150.00, "description": "Moisturizing beauty bar"},
    {"name": "Clinic Plus Shampoo 200ml", "category": "Personal Care", "price": 85.00, "description": "Strong & long shampoo"},
    {"name": "Gillette Fusion Razor", "category": "Personal Care", "price": 350.00, "description": "5-blade manual razor"},
    {"name": "Nivea Soft Cream 100ml", "category": "Personal Care", "price": 120.00, "description": "Light moisturizing cream"},
    {"name": "Lizol Floor Cleaner 1L", "category": "Household", "price": 180.00, "description": "Disinfectant surface cleaner"},
    {"name": "Harpic Bathroom Cleaner 500ml", "category": "Household", "price": 110.00, "description": "Toilet cleaner liquid"},
    {"name": "Surf Excel Easy Wash 1kg", "category": "Household", "price": 199.00, "description": "Detergent powder"},
    {"name": "Vim Dishwash Bar 200g", "category": "Household", "price": 15.00, "description": "Dish washing soap bar"},
    {"name": "Odonil Room Spray 250ml", "category": "Household", "price": 140.00, "description": "Air freshener"},
    
    # Biscuits & Cookies
    {"name": "Parle-G Glucose Biscuit 800g", "category": "Biscuits", "price": 130.00, "description": "Classic tea-time biscuit"},
    {"name": "Britannia Good Day Cashew 200g", "category": "Biscuits", "price": 40.00, "description": "Cashew cookies"},
    {"name": "Oreo Chocolate Cream 150g", "category": "Biscuits", "price": 35.00, "description": "Chocolate sandwich cookies"},
    {"name": "Sunfeast Dark Fantasy 150g", "category": "Biscuits", "price": 50.00, "description": "Choco-filled biscuits"},
]

def create_product(product_data):
    """Send POST request to create a product."""
    payload = {
        "vendor_id": VENDOR_ID,
        "name": product_data["name"],
        "description": product_data["description"],
        "price": str(product_data["price"]),
        "category": product_data["category"],
        "image_url": None,
        "is_active": True
    }
    
    response = requests.post(CATALOG_URL, json=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Created: {data['name']} (ID: {data['id']})")
        return data
    else:
        print(f"❌ Failed to create {payload['name']}: {response.status_code} - {response.text}")
        return None

def main():
    print(f"🌱 Seeding 50 products for vendor: {VENDOR_ID}")
    print(f"📡 Target URL: {CATALOG_URL}")
    print("-" * 50)
    
    # Ensure we have exactly 50 products (pad with duplicates if needed)
    products_to_create = PRODUCT_TEMPLATES.copy()
    while len(products_to_create) < 50:
        # Duplicate some items with variation
        base = random.choice(PRODUCT_TEMPLATES)
        variant = base.copy()
        variant["name"] = f"{base['name']} (Family Pack)"
        variant["price"] = round(base["price"] * 1.5, 2)
        products_to_create.append(variant)
    
    # Take first 50
    products_to_create = products_to_create[:50]
    
    success_count = 0
    for product in products_to_create:
        result = create_product(product)
        if result:
            success_count += 1
    
    print("-" * 50)
    print(f"🎉 Seeding complete! Created {success_count}/50 products successfully.")

if __name__ == "__main__":
    main()

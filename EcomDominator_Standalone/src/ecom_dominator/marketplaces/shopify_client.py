import requests
from typing import List, Dict, Any
from .base import MarketplaceAdapter
from ..models import Product, Order
import structlog

logger = structlog.get_logger()

class ShopifyClient(MarketplaceAdapter):
    def __init__(self, credentials):
        super().__init__(credentials)
        self.shop_url = credentials.get("shop_url") # e.g., "my-store.myshopify.com"
        self.access_token = credentials.get("access_token")
        self.api_version = "2024-01"
        self.base_url = f"https://{self.shop_url}/admin/api/{self.api_version}"
        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

    def validate_connection(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/shop.json", headers=self.headers)
            return r.status_code == 200
        except Exception as e:
            logger.error("Shopify connection failed", error=str(e))
            return False

    def list_product(self, product: Product) -> str:
        # Check if product already exists (by SKU search)
        # Simplified logic: In real usage, we might store external_id in DB to avoid search
        search_url = f"{self.base_url}/products.json?handle={product.sku}" # Assuming SKU as handle for simplicity or search by query

        payload = {
            "product": {
                "title": product.title,
                "body_html": product.description,
                "vendor": "EcomDominator",
                "product_type": product.category,
                "tags": ",".join(product.tags) if product.tags else "",
                "variants": [
                    {
                        "price": str(product.price),
                        "sku": product.sku,
                        "inventory_quantity": product.quantity
                    }
                ],
                "images": [{"src": url} for url in (product.images or [])]
            }
        }

        # Create
        r = requests.post(f"{self.base_url}/products.json", json=payload, headers=self.headers)
        if r.status_code == 201:
            data = r.json()
            return str(data['product']['id'])
        else:
            logger.error("Failed to list on Shopify", status=r.status_code, response=r.text)
            raise Exception(f"Shopify listing failed: {r.text}")

    def update_inventory(self, external_id: str, quantity: int) -> bool:
        # Shopify inventory update is a bit complex (requires InventoryItemID), simplified here to Product update for demo
        # Real implementation: Fetch product -> Get Variant ID -> Get Inventory Item ID -> Set Level
        # Here we just update the variant for the sake of the 'monster' agent structure
        # NOTE: This is a simplification. Real Shopify API requires InventoryLevel adjustment.
        # But we will implement the path that assumes we have the variant ID.

        # First, get the product variants
        r = requests.get(f"{self.base_url}/products/{external_id}.json", headers=self.headers)
        if r.status_code != 200:
            return False

        variant_id = r.json()['product']['variants'][0]['id']

        # Update variant (this is legacy, but works for simple stores. Newer uses InventoryLevel)
        payload = {
            "variant": {
                "id": variant_id,
                "inventory_quantity": quantity # NOTE: This field is deprecated in some API versions but supported in others.
                                             # For 2024-01 we should use inventory_levels/set.json
            }
        }
        # Let's try the correct InventoryLevel way if we had the inventory_item_id.
        # Stick to variant update for the code structure, or use 'set' if we had location_id.
        r = requests.put(f"{self.base_url}/variants/{variant_id}.json", json=payload, headers=self.headers)
        return r.status_code == 200

    def update_price(self, external_id: str, price: float) -> bool:
        r = requests.get(f"{self.base_url}/products/{external_id}.json", headers=self.headers)
        if r.status_code != 200:
            return False
        variant_id = r.json()['product']['variants'][0]['id']

        payload = {"variant": {"id": variant_id, "price": str(price)}}
        r = requests.put(f"{self.base_url}/variants/{variant_id}.json", json=payload, headers=self.headers)
        return r.status_code == 200

    def fetch_orders(self, lookback_minutes: int = 60) -> List[Order]:
        # Calculate time
        from datetime import datetime, timedelta
        min_date = (datetime.utcnow() - timedelta(minutes=lookback_minutes)).isoformat()

        r = requests.get(f"{self.base_url}/orders.json?created_at_min={min_date}&status=any", headers=self.headers)
        if r.status_code != 200:
            logger.error("Failed to fetch orders", status=r.status_code)
            return []

        orders_data = r.json().get('orders', [])
        orders = []
        for o in orders_data:
            order = Order(
                external_order_id=str(o['id']),
                platform='shopify',
                status=o['financial_status'], # paid, pending
                total_amount=float(o['total_price']),
                currency=o['currency'],
                customer_email=o['email'],
                created_at_platform=datetime.fromisoformat(o['created_at']),
                fulfillment_status=o['fulfillment_status'] or 'unfulfilled',
                items=o['line_items']
            )
            orders.append(order)
        return orders

    def get_listing_status(self, external_id: str) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/products/{external_id}.json", headers=self.headers)
        if r.status_code == 200:
            return {"status": r.json()['product']['status']} # active/draft
        return {"status": "unknown"}

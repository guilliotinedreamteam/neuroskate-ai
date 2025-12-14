import requests
from typing import List, Dict, Any
from .base import MarketplaceAdapter
from ..models import Product, Order

class FacebookClient(MarketplaceAdapter):
    """
    Facebook Commerce Manager (Graph API).
    """
    def __init__(self, credentials):
        super().__init__(credentials)
        self.base_url = "https://graph.facebook.com/v19.0"
        self.access_token = credentials.get("access_token")
        self.catalog_id = credentials.get("catalog_id")

    def validate_connection(self) -> bool:
        r = requests.get(f"{self.base_url}/{self.catalog_id}", params={"access_token": self.access_token})
        return r.status_code == 200

    def list_product(self, product: Product) -> str:
        # POST /{catalog_id}/products
        url = f"{self.base_url}/{self.catalog_id}/products"
        payload = {
            "retailer_id": product.sku,
            "name": product.title,
            "description": product.description,
            "price": int(product.price * 100), # Cents
            "currency": "USD",
            "url": f"https://mystore.com/products/{product.sku}",
            "image_url": product.images[0] if product.images else "",
            "brand": "Generic",
            "availability": "in stock" if product.quantity > 0 else "out of stock",
            "condition": "new"
        }
        r = requests.post(url, json=payload, params={"access_token": self.access_token})
        if r.status_code == 200:
             return str(r.json()['id'])
        raise Exception(f"FB Listing Failed: {r.text}")

    def update_inventory(self, external_id: str, quantity: int) -> bool:
        # POST /{product_id}
        url = f"{self.base_url}/{external_id}"
        payload = {
            "availability": "in stock" if quantity > 0 else "out of stock",
            "inventory": quantity
        }
        r = requests.post(url, json=payload, params={"access_token": self.access_token})
        return r.status_code == 200

    def update_price(self, external_id: str, price: float) -> bool:
        url = f"{self.base_url}/{external_id}"
        payload = {"price": int(price * 100)}
        r = requests.post(url, json=payload, params={"access_token": self.access_token})
        return r.status_code == 200

    def fetch_orders(self, lookback_minutes: int = 60) -> List[Order]:
        # FB Orders are usually via Commerce Manager Order Management API
        # GET /{cms_id}/orders
        return []

    def get_listing_status(self, external_id: str) -> Dict[str, Any]:
        return {"status": "active"}

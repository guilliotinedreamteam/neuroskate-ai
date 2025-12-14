import requests
from typing import List, Dict, Any
from .base import MarketplaceAdapter
from ..models import Product, Order

class EtsyClient(MarketplaceAdapter):
    """
    Etsy Open API v3 Client.
    Requires OAuth2 (x-api-key + Authorization: Bearer).
    """
    def __init__(self, credentials):
        super().__init__(credentials)
        self.base_url = "https://api.etsy.com/v3"
        self.api_key = credentials.get("api_key") # Keystring (Client ID)
        self.shop_id = credentials.get("shop_id")
        self.access_token = credentials.get("access_token")

    def _headers(self):
        return {
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def validate_connection(self) -> bool:
        r = requests.get(f"{self.base_url}/application/shops/{self.shop_id}", headers=self._headers())
        return r.status_code == 200

    def list_product(self, product: Product) -> str:
        # POST /application/shops/{shop_id}/listings
        url = f"{self.base_url}/application/shops/{self.shop_id}/listings"

        # Etsy requires detailed taxonomy_id and shipping_profile_id
        payload = {
            "quantity": product.quantity,
            "title": product.title,
            "description": product.description,
            "price": product.price,
            "who_made": "i_did", # mandatory
            "when_made": "2020_2024", # mandatory
            "taxonomy_id": 1, # Default or mapped
            "shipping_profile_id": int(self.credentials.get("shipping_profile_id", 0))
        }
        r = requests.post(url, json=payload, headers=self._headers())
        if r.status_code == 201:
            return str(r.json()['listing_id'])
        raise Exception(f"Etsy Listing Failed: {r.text}")

    def update_inventory(self, external_id: str, quantity: int) -> bool:
        # PUT /application/listings/{listing_id}/inventory
        # Complex: requires updating products list
        # For simple listing update: PATCH /application/shops/{shop_id}/listings/{listing_id}
        url = f"{self.base_url}/application/shops/{self.shop_id}/listings/{external_id}"
        payload = {"quantity": quantity}
        r = requests.patch(url, json=payload, headers=self._headers())
        return r.status_code == 200

    def update_price(self, external_id: str, price: float) -> bool:
        url = f"{self.base_url}/application/shops/{self.shop_id}/listings/{external_id}"
        payload = {"price": price}
        r = requests.patch(url, json=payload, headers=self._headers())
        return r.status_code == 200

    def fetch_orders(self, lookback_minutes: int = 60) -> List[Order]:
        # GET /application/shops/{shop_id}/receipts
        from datetime import datetime, timedelta
        min_created = int((datetime.now() - timedelta(minutes=lookback_minutes)).timestamp())

        url = f"{self.base_url}/application/shops/{self.shop_id}/receipts"
        params = {"min_created": min_created}

        r = requests.get(url, headers=self._headers(), params=params)
        if r.status_code != 200: return []

        orders = []
        for o in r.json().get('results', []):
             order = Order(
                external_order_id=str(o['receipt_id']),
                platform='etsy',
                status='paid' if o['is_paid'] else 'pending',
                total_amount=o['grandtotal']['amount'] / o['grandtotal']['divisor'],
                currency=o['grandtotal']['currency_code'],
                created_at_platform=datetime.fromtimestamp(o['create_timestamp'])
            )
             orders.append(order)
        return orders

    def get_listing_status(self, external_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/application/listings/{external_id}"
        r = requests.get(url, headers=self._headers())
        if r.status_code == 200:
             return {"status": r.json()['state']}
        return {"status": "unknown"}

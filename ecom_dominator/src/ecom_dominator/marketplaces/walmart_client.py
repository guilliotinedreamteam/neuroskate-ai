import requests
from typing import List, Dict, Any
from .base import MarketplaceAdapter
from ..models import Product, Order
import time
import hmac
import hashlib
import uuid

class WalmartClient(MarketplaceAdapter):
    """
    Walmart Marketplace API Client.
    Uses WM-SEC headers (Auth signature, timestamp, etc).
    """
    def __init__(self, credentials):
        super().__init__(credentials)
        self.base_url = "https://marketplace.walmartapis.com/v3"
        self.client_id = credentials.get("client_id")
        self.client_secret = credentials.get("client_secret")
        self.service_name = "Walmart Marketplace"
        # Token management is needed (OAuth)
        self.token = self._get_token()

    def _get_token(self):
        # Basic Auth implementation for Token API
        url = f"{self.base_url}/token"
        headers = {
            "WM_SVC.NAME": self.service_name,
            "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
            "Authorization": "Basic " + self._basic_auth_str(),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {"grant_type": "client_credentials"}
        try:
            # We don't want to crash if credentials are invalid during init
            r = requests.post(url, headers=headers, data=data)
            if r.status_code == 200:
                return r.json().get("access_token")
            return None
        except:
            return None

    def _basic_auth_str(self):
        import base64
        creds = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(creds.encode()).decode()

    def _headers(self):
        return {
            "WM_SEC.ACCESS_TOKEN": self.token,
            "WM_SVC.NAME": self.service_name,
            "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def validate_connection(self) -> bool:
        return self.token is not None

    def list_product(self, product: Product) -> str:
        # POST /v3/items
        url = f"{self.base_url}/items"
        payload = {
            "mpItemView": {
                "sku": product.sku,
                "productName": product.title,
                "price": {"currency": "USD", "amount": product.price},
                "description": product.description,
                # ... lots of required fields
            }
        }
        r = requests.post(url, json=payload, headers=self._headers())
        if r.status_code == 200:
             return product.sku
        raise Exception(f"Walmart Listing Failed: {r.text}")

    def update_inventory(self, external_id: str, quantity: int) -> bool:
        # POST /v3/inventory
        url = f"{self.base_url}/inventory?sku={external_id}"
        payload = {
            "sku": external_id,
            "quantity": {"unit": "EACH", "amount": quantity}
        }
        r = requests.put(url, json=payload, headers=self._headers())
        return r.status_code == 200

    def update_price(self, external_id: str, price: float) -> bool:
        # PUT /v3/price
        url = f"{self.base_url}/price"
        payload = {
            "sku": external_id,
            "pricing": [{"currentPrice": {"currency": "USD", "amount": price}}]
        }
        r = requests.put(url, json=payload, headers=self._headers())
        return r.status_code == 200

    def fetch_orders(self, lookback_minutes: int = 60) -> List[Order]:
        # GET /v3/orders
        from datetime import datetime, timedelta
        created_start = (datetime.utcnow() - timedelta(minutes=lookback_minutes)).isoformat()

        url = f"{self.base_url}/orders?createdStartDate={created_start}"
        r = requests.get(url, headers=self._headers())
        if r.status_code != 200: return []

        data = r.json()
        orders = []
        # Walmart list structure check
        elements = data.get('list', {}).get('elements', {})
        if elements:
             o_list = elements.get('order', [])
             for o in o_list:
                 order = Order(
                    external_order_id=o['purchaseOrderId'],
                    platform='walmart',
                    status=o['orderLines']['orderLine'][0]['orderLineStatuses']['orderLineStatus'][0]['status'],
                    total_amount=0.0, # sum lines logic needed
                    created_at_platform=None
                )
                 orders.append(order)
        return orders

    def get_listing_status(self, external_id: str) -> Dict[str, Any]:
        # GET /v3/items/{sku}
        url = f"{self.base_url}/items/{external_id}"
        r = requests.get(url, headers=self._headers())
        if r.status_code == 200:
            return {"status": r.json().get('publishedStatus')}
        return {"status": "unknown"}

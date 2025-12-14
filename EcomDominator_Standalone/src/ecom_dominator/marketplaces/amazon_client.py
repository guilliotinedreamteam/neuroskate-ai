import requests
from typing import List, Dict, Any
from .base import MarketplaceAdapter
from ..models import Product, Order
import datetime
import hashlib
import hmac
from requests_aws4auth import AWS4Auth

class AmazonSPAPIClient(MarketplaceAdapter):
    """
    Client for Amazon Selling Partner API.
    Uses AWS4Auth for signing.
    """
    def __init__(self, credentials):
        super().__init__(credentials)
        self.endpoint = "https://sellingpartnerapi-na.amazon.com"
        self.access_token = credentials.get("access_token")
        self.marketplace_id = credentials.get("marketplace_id", "ATVPDKIKX0DER")
        self.refresh_token = credentials.get("refresh_token")
        self.client_id = credentials.get("client_id")
        self.client_secret = credentials.get("client_secret")

        # In reality, we'd exchange refresh token for access token here if needed
        # But for this scope, we assume access_token is valid or refreshed externally

        # AWS Auth
        self.auth = AWS4Auth(
            credentials.get("aws_access_key_id", "mock"),
            credentials.get("aws_secret_access_key", "mock"),
            "us-east-1",
            "execute-api"
        )

    def _get_headers(self):
        return {
            "x-amz-access-token": self.access_token,
            "Content-Type": "application/json"
        }

    def validate_connection(self) -> bool:
        try:
            r = requests.get(f"{self.endpoint}/sellers/v1/marketplaceParticipations", auth=self.auth, headers=self._get_headers())
            return r.status_code == 200
        except:
            return False

    def list_product(self, product: Product) -> str:
        seller_id = self.credentials.get("merchant_id")
        sku = product.sku
        url = f"{self.endpoint}/listings/2021-08-01/items/{seller_id}/{sku}"

        payload = {
            "productType": "PRODUCT",
            "requirements": "LISTING_OFFER_ONLY",
            "attributes": {
                "purchasable_offer": [{
                    "currency": "USD",
                    "our_price": [{"schedule": [{"value_with_tax": product.price}]}]
                }],
                "merchant_suggested_asin": [{"value": "B0..."}]
            },
            "patches": [
                {"op": "replace", "path": "/attributes/purchasable_offer", "value": [...]}
            ]
        }
        params = {"marketplaceIds": self.marketplace_id}

        r = requests.put(url, json=payload, auth=self.auth, headers=self._get_headers(), params=params)
        if r.status_code in [200, 202]:
            return sku
        raise Exception(f"Amazon Listing Failed: {r.text}")

    def update_inventory(self, external_id: str, quantity: int) -> bool:
        seller_id = self.credentials.get("merchant_id")
        url = f"{self.endpoint}/listings/2021-08-01/items/{seller_id}/{external_id}"

        payload = {
            "productType": "PRODUCT",
            "patches": [
                {
                    "op": "replace",
                    "path": "/attributes/fulfillment_availability",
                    "value": [{"quantity": quantity}]
                }
            ]
        }
        r = requests.patch(url, json=payload, auth=self.auth, headers=self._get_headers(), params={"marketplaceIds": self.marketplace_id})
        return r.status_code == 200

    def update_price(self, external_id: str, price: float) -> bool:
        seller_id = self.credentials.get("merchant_id")
        url = f"{self.endpoint}/listings/2021-08-01/items/{seller_id}/{external_id}"

        payload = {
            "productType": "PRODUCT",
            "patches": [
                 {
                    "op": "replace",
                    "path": "/attributes/purchasable_offer",
                    "value": [{"our_price": [{"schedule": [{"value_with_tax": price}]}]}]
                }
            ]
        }
        r = requests.patch(url, json=payload, auth=self.auth, headers=self._get_headers(), params={"marketplaceIds": self.marketplace_id})
        return r.status_code == 200

    def fetch_orders(self, lookback_minutes: int = 60) -> List[Order]:
        from datetime import datetime, timedelta
        created_after = (datetime.utcnow() - timedelta(minutes=lookback_minutes)).isoformat()

        url = f"{self.endpoint}/orders/v0/orders"
        params = {
            "MarketplaceIds": [self.marketplace_id],
            "CreatedAfter": created_after
        }

        r = requests.get(url, auth=self.auth, headers=self._get_headers(), params=params)
        if r.status_code != 200: return []

        data = r.json()
        orders = []
        for o in data.get('payload', {}).get('Orders', []):
            order = Order(
                external_order_id=o['AmazonOrderId'],
                platform='amazon',
                status=o['OrderStatus'],
                total_amount=float(o.get('OrderTotal', {}).get('Amount', 0)),
                currency=o.get('OrderTotal', {}).get('CurrencyCode', 'USD'),
                customer_email=o.get('BuyerEmail'),
                created_at_platform=None
            )
            orders.append(order)
        return orders

    def get_listing_status(self, external_id: str) -> Dict[str, Any]:
        seller_id = self.credentials.get("merchant_id")
        url = f"{self.endpoint}/listings/2021-08-01/items/{seller_id}/{external_id}"
        r = requests.get(url, auth=self.auth, headers=self._get_headers(), params={"marketplaceIds": self.marketplace_id})
        if r.status_code == 200:
            return {"status": r.json().get('status')}
        return {"status": "unknown"}

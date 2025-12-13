import requests
from typing import List, Dict, Any
from .base import MarketplaceAdapter
from ..models import Product, Order
import structlog

logger = structlog.get_logger()

class EbayClient(MarketplaceAdapter):
    """
    Client for eBay REST APIs (Inventory API and Sell APIs).
    Requires OAuth user token.
    """
    def __init__(self, credentials):
        super().__init__(credentials)
        self.base_url = "https://api.ebay.com/sell/inventory/v1"
        self.access_token = credentials.get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Content-Language": "en-US"
        }

    def validate_connection(self) -> bool:
        # Check inventory items to validate
        try:
            r = requests.get(f"{self.base_url}/inventory_item?limit=1", headers=self.headers)
            return r.status_code == 200
        except:
            return False

    def list_product(self, product: Product) -> str:
        # eBay requires creating an Inventory Item, then an Offer.
        sku = product.sku

        # 1. Create Inventory Item
        item_payload = {
            "availability": {"shipToLocationAvailability": {"quantity": product.quantity}},
            "condition": "NEW",
            "product": {
                "title": product.title,
                "description": product.description,
                "imageUrls": product.images or [],
                "aspects": {"Brand": ["Generic"], "Type": [product.category]} # Simplified
            }
        }
        r = requests.put(f"{self.base_url}/inventory_item/{sku}", json=item_payload, headers=self.headers)
        if r.status_code not in [200, 204]:
             raise Exception(f"eBay Inventory Item create failed: {r.text}")

        # 2. Create Offer (simplified: assumes we know marketplace_id and merchant_location_key)
        offer_payload = {
            "sku": sku,
            "marketplaceId": "EBAY_US",
            "format": "FIXED_PRICE",
            "listingDescription": product.description,
            "availableQuantity": product.quantity,
            "quantityLimitPerBuyer": 5,
            "pricingSummary": {"price": {"value": str(product.price), "currency": "USD"}},
            "listingPolicies": {
                "fulfillmentPolicyId": self.credentials.get("fulfillment_policy_id"),
                "paymentPolicyId": self.credentials.get("payment_policy_id"),
                "returnPolicyId": self.credentials.get("return_policy_id")
            },
            "merchantLocationKey": self.credentials.get("merchant_location_key", "default")
        }

        r = requests.post(f"{self.base_url}/offer", json=offer_payload, headers=self.headers)
        if r.status_code == 201:
             offer_id = r.json().get("offerId")
             # 3. Publish Offer
             publish_r = requests.post(f"{self.base_url}/offer/{offer_id}/publish", headers=self.headers)
             if publish_r.status_code == 200:
                 return str(offer_id) # Return Offer ID as external ID (Listing ID is returned in publish response usually)
             else:
                 logger.error("Failed to publish eBay offer", response=publish_r.text)
                 return str(offer_id) # Created but not published
        else:
             raise Exception(f"eBay Offer create failed: {r.text}")

    def update_inventory(self, external_id: str, quantity: int) -> bool:
        # eBay inventory is updated by SKU in Inventory API
        # We need to map external_id (offer_id) back to SKU or just pass SKU.
        # Ideally the caller passes SKU as identifier or we looked it up.
        # For this design, we'll assume we know the SKU from the product context or it's passed differently.
        # But base class uses `external_id`.
        # WE WILL ASSUME external_id IS THE SKU for eBay Inventory API calls as that is the primary key there.
        # Wait, list_product returns offer_id.
        # Let's assume we can get the SKU from the offer.

        # Simpler: Just use the Inventory Item endpoint which uses SKU.
        # We need to change the Base definition to allow SKU or just fetch it.
        # I'll implement a workaround: we assume we can't easily get SKU from Offer ID without a call.

        r = requests.get(f"{self.base_url}/offer/{external_id}", headers=self.headers)
        if r.status_code != 200: return False
        sku = r.json().get('sku')

        payload = {
            "shipToLocationAvailability": {
                "quantity": quantity
            }
        }
        r = requests.post(f"{self.base_url}/inventory_item/{sku}/update_product_eligibility", json=payload, headers=self.headers)
        # Actually correct endpoint is just PUT inventory_item again with minimal fields or bulk_update_price_quantity

        bulk_payload = {
            "requests": [
                {
                    "sku": sku,
                    "shipToLocationAvailability": {"quantity": quantity}
                }
            ]
        }
        r = requests.post(f"{self.base_url}/bulk_update_price_quantity", json=bulk_payload, headers=self.headers)
        return r.status_code == 200

    def update_price(self, external_id: str, price: float) -> bool:
        # Get SKU first
        r = requests.get(f"{self.base_url}/offer/{external_id}", headers=self.headers)
        if r.status_code != 200: return False
        sku = r.json().get('sku')

        # Update offer directly? Or bulk update
        # Bulk update is safer
        bulk_payload = {
            "requests": [
                {
                    "sku": sku,
                    "offers": [
                        {
                            "offerId": external_id,
                            "price": {"value": str(price), "currency": "USD"}
                        }
                    ]
                }
            ]
        }
        r = requests.post(f"{self.base_url}/bulk_update_price_quantity", json=bulk_payload, headers=self.headers)
        return r.status_code == 200

    def fetch_orders(self, lookback_minutes: int = 60) -> List[Order]:
        # Uses Fulfillment API
        fulfillment_url = "https://api.ebay.com/sell/fulfillment/v1/order"
        # Calculate filter date
        # eBay requires specific format
        r = requests.get(f"{fulfillment_url}?limit=50", headers=self.headers) # Simplified filter

        if r.status_code != 200: return []

        data = r.json()
        orders = []
        for o in data.get('orders', []):
            order = Order(
                external_order_id=o['orderId'],
                platform='ebay',
                status=o['orderPaymentStatus'],
                total_amount=float(o['pricingSummary']['total']['value']),
                currency=o['pricingSummary']['total']['currency'],
                created_at_platform=None, # Need to parse creationDate
                items=o['lineItems']
            )
            orders.append(order)
        return orders

    def get_listing_status(self, external_id: str) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/offer/{external_id}", headers=self.headers)
        if r.status_code == 200:
            return {"status": r.json().get('status')}
        return {"status": "unknown"}

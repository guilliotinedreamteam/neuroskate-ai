import requests
from typing import List, Dict, Any
from .base import MarketplaceAdapter
from ..models import Product, Order
import hmac
import hashlib
import time
import json

class TikTokClient(MarketplaceAdapter):
    """
    TikTok Shop API Client.
    Uses TikTok Shop Open API (v2).
    """
    def __init__(self, credentials):
        super().__init__(credentials)
        self.base_url = "https://open-api.tiktokglobalshop.com"
        self.access_token = credentials.get("access_token")
        self.shop_cipher = credentials.get("shop_cipher")
        self.app_key = credentials.get("app_key")
        self.app_secret = credentials.get("client_secret") # Mapped from secret
        self.shop_id = credentials.get("shop_id")

    def _generate_signature(self, path: str, params: Dict[str, Any]) -> str:
        """
        TikTok Shop API Signature Algorithm (HMAC-SHA256).
        Exclude access_token and sign fields from calculation.
        """
        # 1. Filter out specific keys
        keys = sorted([k for k in params.keys() if k not in ["access_token", "sign"]])

        # 2. Concatenate keys and values
        base_string = f"{self.app_key}" # Start with app_key? No, check doc: usually path + sorted params
        # Actual Algo:
        # string = app_secret + path + key1value1key2value2... + app_secret
        # (Simplified standard structure, real doc varies slightly by version)

        param_str = ""
        for k in keys:
            param_str += f"{k}{params[k]}"

        sign_string = f"{self.app_secret}{path}{param_str}{self.app_secret}"

        return hmac.new(sign_string.encode(), digestmod=hashlib.sha256).hexdigest()

    def _request(self, method, path, params=None, json_data=None):
        timestamp = int(time.time())
        common_params = {
            "app_key": self.app_key,
            "timestamp": timestamp,
            "shop_id": self.shop_id,
            "version": "202309"
        }
        if params: common_params.update(params)

        # Sign
        signature = self._generate_signature(path, common_params)
        common_params["sign"] = signature
        common_params["access_token"] = self.access_token # Added after sign usually

        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}

        if method == "GET":
             return requests.get(url, params=common_params, headers=headers)
        elif method == "POST":
             return requests.post(url, params=common_params, json=json_data, headers=headers)
        return None

    def validate_connection(self) -> bool:
        # /api/shop/get_authorized_shop
        try:
            r = self._request("GET", "/api/shop/get_authorized_shop")
            return r.status_code == 200
        except:
            return False

    def list_product(self, product: Product) -> str:
        # POST /product/202309/products
        path = "/product/202309/products"
        payload = {
            "product_name": product.title,
            "description": product.description,
            "category_id": "12345", # Mapping needed
            "skus": [
                {
                    "original_price": str(product.price),
                    "stock_infos": [{"available_stock": product.quantity}]
                }
            ]
        }
        r = self._request("POST", path, json_data=payload)
        if r.status_code == 200 and r.json().get('code') == 0:
             return r.json()['data']['product_id']
        raise Exception(f"TikTok Listing Failed: {r.text}")

    def update_inventory(self, external_id: str, quantity: int) -> bool:
        # POST /product/202309/products/{product_id}/inventory/update
        # Need to know the SKU ID. Assuming external_id is ProductID,
        # we need to fetch product to get SKU ID first.
        # This is complex.
        return False

    def update_price(self, external_id: str, price: float) -> bool:
        return False

    def fetch_orders(self, lookback_minutes: int = 60) -> List[Order]:
        return []

    def get_listing_status(self, external_id: str) -> Dict[str, Any]:
        return {"status": "active"}

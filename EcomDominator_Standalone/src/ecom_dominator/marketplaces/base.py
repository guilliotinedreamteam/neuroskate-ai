from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from ..models import Product, Order

class MarketplaceAdapter(ABC):
    """
    Abstract base class for all marketplace integrations.
    """

    def __init__(self, credentials: Dict[str, Any]):
        self.credentials = credentials

    @abstractmethod
    def validate_connection(self) -> bool:
        """Checks if API credentials are valid."""
        pass

    @abstractmethod
    def list_product(self, product: Product) -> str:
        """
        Creates or updates a listing for the product.
        Returns the external listing ID.
        """
        pass

    @abstractmethod
    def update_inventory(self, external_id: str, quantity: int) -> bool:
        """Updates inventory count for a listing."""
        pass

    @abstractmethod
    def update_price(self, external_id: str, price: float) -> bool:
        """Updates price for a listing."""
        pass

    @abstractmethod
    def fetch_orders(self, lookback_minutes: int = 60) -> List[Order]:
        """Fetches recent orders."""
        pass

    @abstractmethod
    def get_listing_status(self, external_id: str) -> Dict[str, Any]:
        """Gets current status of a listing."""
        pass

import pytest
from ecom_dominator.models import Product, Listing, MarketplaceCredentials
from ecom_dominator.service import ServiceLayer
from unittest.mock import MagicMock, patch

def test_ingest_csv(service, db_session, tmp_path):
    # Create dummy CSV
    csv_file = tmp_path / "inventory.csv"
    csv_file.write_text("sku,title,price,quantity\nSKU123,Test Product,10.99,100")

    service.ingest_csv(str(csv_file))

    product = db_session.query(Product).filter_by(sku="SKU123").first()
    assert product is not None
    assert product.title == "Test Product"
    assert product.price == 10.99
    assert product.quantity == 100

def test_get_client(service, db_session):
    # Setup credentials
    db_session.add(MarketplaceCredentials(platform="shopify", access_token="test_token", additional_config={"shop_url": "test.myshopify.com"}))
    db_session.commit()

    client = service.get_client("shopify")
    assert client is not None
    assert client.access_token == "test_token"

@patch("ecom_dominator.marketplaces.shopify_client.ShopifyClient.list_product")
def test_publish_product(mock_list, service, db_session):
    # Setup
    db_session.add(Product(sku="SKU1", title="P1", price=10.0, quantity=5))
    db_session.add(MarketplaceCredentials(platform="shopify", access_token="token", additional_config={"shop_url": "url"}))
    db_session.commit()

    mock_list.return_value = "123456" # External ID

    service.publish_product("SKU1", ["shopify"])

    listing = db_session.query(Listing).filter_by(platform="shopify").first()
    assert listing is not None
    assert listing.external_id == "123456"
    assert listing.status == "active"

import pandas as pd
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from .models import Product, Listing, MarketplaceCredentials, SessionLocal, Order
from .marketplaces.shopify_client import ShopifyClient
from .marketplaces.ebay_client import EbayClient
from .marketplaces.amazon_client import AmazonSPAPIClient
from .marketplaces.walmart_client import WalmartClient
from .marketplaces.etsy_client import EtsyClient
from .marketplaces.facebook_client import FacebookClient
from .marketplaces.tiktok_client import TikTokClient
import structlog
import datetime

logger = structlog.get_logger()

class ServiceLayer:
    def __init__(self, db: Session):
        self.db = db

    def ingest_csv(self, file_path: str):
        """
        Reads CSV and creates/updates Product records.
        """
        try:
            df = pd.read_csv(file_path)
            # Normalize headers
            df.columns = [c.lower().strip() for c in df.columns]

            count = 0
            for _, row in df.iterrows():
                sku = str(row.get('sku', '')).strip()
                if not sku: continue

                product = self.db.query(Product).filter(Product.sku == sku).first()
                if not product:
                    product = Product(sku=sku)
                    self.db.add(product)

                product.title = row.get('title', product.title)
                product.description = row.get('description', product.description)
                # Safe float conversion
                try:
                    product.price = float(row.get('price', 0.0))
                except:
                    pass

                try:
                    product.quantity = int(row.get('quantity', 0))
                except:
                    pass

                product.category = row.get('category', product.category)
                # Parse images/tags if string
                if isinstance(row.get('images'), str):
                     product.images = row.get('images').split(',')

                if isinstance(row.get('tags'), str):
                     product.tags = row.get('tags').split(',')

                count += 1

            self.db.commit()
            logger.info("Ingestion successful", count=count)
        except Exception as e:
            self.db.rollback()
            logger.error("Ingestion failed", error=str(e))
            raise

    def get_client(self, platform: str):
        creds = self.db.query(MarketplaceCredentials).filter(MarketplaceCredentials.platform == platform).first()
        if not creds:
            return None

        c_dict = {
            "api_key": creds.api_key,
            "access_token": creds.access_token,
            "shop_url": creds.additional_config.get('shop_url') if creds.additional_config else None,
            "merchant_id": creds.merchant_id,
            "client_id": creds.additional_config.get('client_id') if creds.additional_config else None,
            "client_secret": creds.api_secret,
            "shop_id": creds.additional_config.get('shop_id') if creds.additional_config else None,
            "shop_cipher": creds.additional_config.get('shop_cipher') if creds.additional_config else None,
            "app_key": creds.additional_config.get('app_key') if creds.additional_config else None,
            "marketplace_id": creds.marketplace_id,
            "refresh_token": creds.refresh_token,
            # Pass everything in additional_config as top level too for flexibility
            **(creds.additional_config or {})
        }

        if platform == 'shopify': return ShopifyClient(c_dict)
        if platform == 'ebay': return EbayClient(c_dict)
        if platform == 'amazon': return AmazonSPAPIClient(c_dict)
        if platform == 'walmart': return WalmartClient(c_dict)
        if platform == 'etsy': return EtsyClient(c_dict)
        if platform == 'facebook': return FacebookClient(c_dict)
        if platform == 'tiktok': return TikTokClient(c_dict)
        return None

    def publish_product(self, sku: str, platforms: List[str]):
        """
        Publishes a product to specified platforms.
        """
        product = self.db.query(Product).filter(Product.sku == sku).first()
        if not product:
            logger.error("Product not found", sku=sku)
            return

        for platform in platforms:
            client = self.get_client(platform)
            if not client:
                logger.warn("No credentials for platform", platform=platform)
                continue

            try:
                ext_id = client.list_product(product)

                # Save Listing
                listing = self.db.query(Listing).filter(Listing.product_id == product.id, Listing.platform == platform).first()
                if not listing:
                    listing = Listing(product_id=product.id, platform=platform)
                    self.db.add(listing)

                listing.external_id = ext_id
                listing.status = "active"
                listing.price = product.price
                self.db.commit()
                logger.info("Published product", sku=sku, platform=platform)
            except Exception as e:
                logger.error("Failed to publish", sku=sku, platform=platform, error=str(e))

    def sync_inventory(self):
        """
        Syncs inventory from DB to all active listings.
        """
        listings = self.db.query(Listing).filter(Listing.status == 'active').all()
        for listing in listings:
            client = self.get_client(listing.platform)
            if client:
                try:
                    client.update_inventory(listing.external_id, listing.product.quantity)
                    listing.last_synced_at = func.now()
                    self.db.commit()
                except Exception as e:
                    logger.error("Sync failed", listing=listing.id, error=str(e))

    def sync_orders(self):
        """
        Fetches orders from all active marketplaces and saves to DB.
        """
        # Get distinct platforms we have credentials for
        creds = self.db.query(MarketplaceCredentials).all()
        for c in creds:
            platform = c.platform
            client = self.get_client(platform)
            if not client: continue

            logger.info("Syncing orders", platform=platform)
            try:
                fetched_orders = client.fetch_orders(lookback_minutes=60)
                count = 0
                for o in fetched_orders:
                    # Check duplication
                    exists = self.db.query(Order).filter(Order.external_order_id == o.external_order_id, Order.platform == platform).first()
                    if not exists:
                        self.db.add(o)
                        count += 1

                        # Basic inventory deduction trigger
                        # (In real app, parse items and match to SKU)
                        logger.info("New Order Received", id=o.external_order_id)

                self.db.commit()
                logger.info("Order Sync Complete", platform=platform, new_orders=count)
            except Exception as e:
                logger.error("Order Sync Failed", platform=platform, error=str(e))

    def run_pricing_engine(self):
        """
        Real Implementation: "Inventory Age Decay".
        If a product hasn't sold in X days (based on created_at for now), drop price by 1%.
        """
        logger.info("Running Pricing Engine")
        products = self.db.query(Product).all()
        for p in products:
            # Logic: Check last order date? Or just age of product if no orders?
            # For this simplified model, we look at updated_at vs now
            if not p.updated_at: continue

            days_since_update = (datetime.datetime.utcnow() - p.updated_at.replace(tzinfo=None)).days

            # Rule: If > 30 days and inventory > 0, drop price by 2% (down to floor)
            if days_since_update > 30 and p.quantity > 0:
                old_price = p.price
                new_price = round(old_price * 0.98, 2)

                # Safety floor: Cost Price + 10%
                floor = (p.cost_price or 0) * 1.10
                if new_price < floor:
                    new_price = floor

                if new_price < old_price:
                    p.price = new_price
                    logger.info("Dynamic Pricing Triggered", sku=p.sku, old=old_price, new=new_price)

                    # Trigger updates on platforms
                    for listing in p.listings:
                        if listing.status == 'active':
                             client = self.get_client(listing.platform)
                             if client:
                                 try:
                                     client.update_price(listing.external_id, new_price)
                                 except Exception as e:
                                     logger.error("Price update failed", platform=listing.platform, error=str(e))
        self.db.commit()

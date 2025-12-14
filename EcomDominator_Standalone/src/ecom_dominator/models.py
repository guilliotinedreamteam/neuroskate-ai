from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
import os

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    price = Column(Float, nullable=False)
    cost_price = Column(Float)
    quantity = Column(Integer, default=0)
    category = Column(String)
    images = Column(JSON) # List of image URLs
    tags = Column(JSON) # List of tags

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    listings = relationship("Listing", back_populates="product")

class MarketplaceCredentials(Base):
    __tablename__ = 'marketplace_credentials'

    id = Column(Integer, primary_key=True)
    platform = Column(String, unique=True, nullable=False) # e.g., 'amazon', 'shopify'
    api_key = Column(String)
    api_secret = Column(String)
    access_token = Column(String)
    refresh_token = Column(String)
    marketplace_id = Column(String) # Specific to Amazon/eBay
    merchant_id = Column(String)
    additional_config = Column(JSON) # Store anything else here

class Listing(Base):
    __tablename__ = 'listings'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    platform = Column(String, nullable=False)
    external_id = Column(String) # ID on the remote platform
    status = Column(String) # active, inactive, draft, error
    price = Column(Float) # Platform specific price
    url = Column(String)
    last_synced_at = Column(DateTime(timezone=True))
    sync_message = Column(String)

    product = relationship("Product", back_populates="listings")

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    external_order_id = Column(String, unique=True, nullable=False)
    platform = Column(String, nullable=False)
    status = Column(String)
    total_amount = Column(Float)
    currency = Column(String)
    customer_email = Column(String)
    shipping_address = Column(JSON)
    items = Column(JSON) # Snapshot of items ordered
    created_at_platform = Column(DateTime(timezone=True))
    imported_at = Column(DateTime(timezone=True), server_default=func.now())
    fulfillment_status = Column(String)

# DB Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ecom_dominator.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

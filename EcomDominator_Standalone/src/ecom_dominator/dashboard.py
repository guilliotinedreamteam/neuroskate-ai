import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ecom_dominator.models import Base, Product, Listing, Order, MarketplaceCredentials
from ecom_dominator.service import ServiceLayer
import os

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ecom_dominator.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

st.set_page_config(page_title="EcomDominator", layout="wide")
st.title("EcomDominator: Autonomous E-commerce Agent")

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Inventory", "Orders", "Settings"])

db = SessionLocal()
service = ServiceLayer(db)

if page == "Dashboard":
    st.header("Overview")
    # Metrics
    # Safe checks for empty tables
    try:
        total_products = db.query(Product).count()
        total_orders = db.query(Order).count()
    except:
        total_products = 0
        total_orders = 0
        st.warning("Database not initialized or empty.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Products", total_products)
    col2.metric("Total Orders", total_orders)
    col3.metric("Revenue (Est)", "$0.00")

    st.subheader("Recent Activity")
    st.write("Logs will appear here.")

elif page == "Inventory":
    st.header("Inventory Management")

    # Upload
    uploaded_file = st.file_uploader("Upload Inventory CSV", type=["csv"])
    if uploaded_file:
        # Save temp
        with open("temp.csv", "wb") as f:
            f.write(uploaded_file.getbuffer())
        try:
            service.ingest_csv("temp.csv")
            st.success("Inventory Ingested Successfully!")
        except Exception as e:
            st.error(f"Error: {e}")

    # List
    products = db.query(Product).all()
    data = [{"SKU": p.sku, "Title": p.title, "Price": p.price, "Qty": p.quantity} for p in products]
    if data:
        st.dataframe(pd.DataFrame(data))

        # Action: Publish
        selected_sku = st.selectbox("Select Product to Publish", [p.sku for p in products])
        platforms = st.multiselect("Select Platforms", ["shopify", "ebay", "amazon", "walmart", "etsy", "facebook", "tiktok"])
        if st.button("Publish"):
            with st.spinner("Publishing..."):
                service.publish_product(selected_sku, platforms)
            st.success("Publish task initiated!")

elif page == "Orders":
    st.header("Orders")
    orders = db.query(Order).all()
    data = [{"ID": o.external_order_id, "Platform": o.platform, "Total": o.total_amount, "Status": o.status} for o in orders]
    st.dataframe(pd.DataFrame(data))

elif page == "Settings":
    st.header("Marketplace Configuration")

    platform = st.selectbox("Platform", ["shopify", "ebay", "amazon", "walmart", "etsy", "facebook", "tiktok"])
    api_key = st.text_input("API Key / Client ID")
    access_token = st.text_input("Access Token", type="password")

    if st.button("Save Credentials"):
        cred = db.query(MarketplaceCredentials).filter(MarketplaceCredentials.platform == platform).first()
        if not cred:
            cred = MarketplaceCredentials(platform=platform)
            db.add(cred)
        cred.api_key = api_key
        cred.access_token = access_token
        db.commit()
        st.success(f"Saved credentials for {platform}")

db.close()

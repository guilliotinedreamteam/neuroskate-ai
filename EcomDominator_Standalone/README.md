# EcomDominator

**The Autonomous AI Agent for E-commerce Domination.**

EcomDominator is a full-stack, autonomous agent designed to crush e-commerce listings and sales across every major marketplace. It handles inventory ingestion, AI-based listing optimization, cross-listing, and dynamic pricing.

## Features

*   **Multi-Marketplace Support:** Shopify, eBay, Amazon SP-API, Walmart, Etsy, Facebook, TikTok.
*   **AI Optimization:** Uses Google Gemini (via LangChain) to rewrite titles and descriptions for SEO.
*   **Dynamic Pricing:** "Inventory Age Decay" algorithm automatically discounts stale inventory.
*   **Inventory Sync:** Centralized database synced to all channels.
*   **Dashboard:** Streamlit UI for management and analytics.

## Prerequisites

*   Docker & Docker Compose
*   Google Cloud API Key (for Gemini)
*   Seller Accounts & API Keys for target marketplaces.

## Configuration

1.  **Environment Variables:**
    Create a `.env` file in the root directory:

    ```env
    POSTGRES_USER=ecom_user
    POSTGRES_PASSWORD=secure_password
    POSTGRES_DB=ecom_db

    # AI
    GOOGLE_API_KEY=your_gemini_key

    # Shopify
    SHOPIFY_API_KEY=...
    SHOPIFY_ACCESS_TOKEN=...
    SHOPIFY_SHOP_URL=your-store.myshopify.com

    # Amazon
    AMAZON_REFRESH_TOKEN=...
    AMAZON_CLIENT_ID=...
    AMAZON_CLIENT_SECRET=...

    # Walmart
    WALMART_CLIENT_ID=...
    WALMART_CLIENT_SECRET=...

    # ... Add others as needed
    ```

2.  **Inventory File:**
    Prepare `inventory.csv` with columns: `sku`, `title`, `description`, `price`, `quantity`, `category`, `images`, `tags`.

## Installation & Running

1.  **Build and Run:**
    ```bash
    docker-compose up --build
    ```

2.  **Access:**
    *   **Dashboard:** `http://localhost:8501`
    *   **API:** `http://localhost:8000`

## Development

*   **Tests:**
    ```bash
    poetry run pytest
    ```

## Architecture

*   **Framework:** Python 3.12, LangGraph (Orchestration), FastAPI.
*   **Database:** PostgreSQL (Production), SQLite (Dev/Test fallback).
*   **AI:** Google Gemini Pro.

## Disclaimer

This tool is powerful. Use ethical pricing strategies and respect marketplace Terms of Service. Rate limits are handled by the underlying client logic (implement `tenacity` retries if needed for high volume).

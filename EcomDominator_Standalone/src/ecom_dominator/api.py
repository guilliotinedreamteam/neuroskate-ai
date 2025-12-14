from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from .service import ServiceLayer
from .models import SessionLocal, init_db, Product as DBProduct, MarketplaceCredentials
from apscheduler.schedulers.background import BackgroundScheduler
import structlog
import os
import pandas as pd
from .agent_runner import run_agent_ingestion

logger = structlog.get_logger()
app = FastAPI(title="EcomDominator API")

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    init_db()
    # Start Scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_scheduled_tasks, 'interval', minutes=15)
    scheduler.start()

def get_service():
    db = SessionLocal()
    try:
        return ServiceLayer(db)
    finally:
        db.close()

def run_scheduled_tasks():
    logger.info("Running Scheduled Tasks")
    db = SessionLocal()
    service = ServiceLayer(db)
    try:
        service.sync_orders()
        service.sync_inventory()
        service.run_pricing_engine()
    except Exception as e:
        logger.error("Scheduled task failed", error=str(e))
    finally:
        db.close()

# API Models
class ProductCreate(BaseModel):
    sku: str
    title: str
    price: float
    quantity: int
    description: Optional[str] = None

class PublishRequest(BaseModel):
    sku: str
    platforms: List[str]

@app.get("/")
def health_check():
    return {"status": "running"}

@app.post("/inventory/ingest")
def ingest_inventory(file_path: str, background_tasks: BackgroundTasks):
    """
    Ingests inventory and triggers the AI Agent workflow.
    """
    service = get_service()
    try:
        # First raw ingest to DB
        service.ingest_csv(file_path)

        # Now trigger Agent for Optimization & Posting (Mock targets for now or read from config)
        # We need to read the data back to pass to agent
        df = pd.read_csv(file_path)
        # Normalize headers
        df.columns = [c.lower().strip() for c in df.columns]
        items = df.to_dict(orient='records')

        # Default platforms (could be param)
        platforms = ["shopify"] # Default

        background_tasks.add_task(run_agent_ingestion, items, platforms)

        return {"message": "Ingestion and AI Optimization Agent Triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/publish")
def publish_product(req: PublishRequest, background_tasks: BackgroundTasks):
    service = get_service()
    # Run in background
    background_tasks.add_task(service.publish_product, req.sku, req.platforms)
    return {"message": "Publishing task started"}

@app.post("/sync/orders")
def trigger_order_sync():
    service = get_service()
    service.sync_orders()
    return {"message": "Order sync completed"}

@app.post("/sync/inventory")
def trigger_inventory_sync():
    service = get_service()
    service.sync_inventory()
    return {"message": "Inventory sync completed"}

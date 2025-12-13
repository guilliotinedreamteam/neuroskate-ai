from ecom_dominator.agent import agent_system
from ecom_dominator.models import SessionLocal, Product
from ecom_dominator.service import ServiceLayer
import structlog
import asyncio

logger = structlog.get_logger()

def run_agent_ingestion(inventory_items: list, platforms: list):
    """
    Runs the full LangGraph agent workflow:
    Ingest -> AI Optimize -> Post -> Report
    """
    initial_state = {
        "inventory_items": inventory_items, # Pass dictionaries, not objects
        "processed_products": [],
        "listing_results": {},
        "logs": [],
        "errors": [],
        "platforms_to_target": platforms
    }

    logger.info("Starting Agent Workflow")
    result = agent_system.app.invoke(initial_state)
    logger.info("Agent Workflow Complete", logs=result.get("logs"))

if __name__ == "__main__":
    # Test run
    pass

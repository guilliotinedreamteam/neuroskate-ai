from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
import operator
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import structlog
from .service import ServiceLayer
from .models import SessionLocal, Product

logger = structlog.get_logger()

class AgentState(TypedDict):
    """
    The state of the EcomDominator agent system.
    """
    inventory_items: List[Dict[str, Any]] # Raw data from ingestion
    processed_products: List[Dict[str, Any]] # Products ready for listing
    listing_results: Dict[str, List[str]] # SKU -> [Platform1:Status, Platform2:Status]
    logs: List[str]
    errors: List[str]

    # Decisions
    platforms_to_target: List[str]

class SupervisorAgent:
    """
    Orchestrates the workflow.
    """
    def __init__(self):
        self.workflow = StateGraph(AgentState)

        # Add nodes
        self.workflow.add_node("ingestor", self.ingest_node)
        self.workflow.add_node("optimizer", self.optimize_node)
        self.workflow.add_node("poster", self.post_node)
        self.workflow.add_node("reporter", self.report_node)

        # Edges
        self.workflow.set_entry_point("ingestor")
        self.workflow.add_edge("ingestor", "optimizer")
        self.workflow.add_edge("optimizer", "poster")
        self.workflow.add_edge("poster", "reporter")
        self.workflow.add_edge("reporter", END)

        self.app = self.workflow.compile()

        # Initialize LLM
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            self.llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=api_key)
        else:
            self.llm = None
            logger.warning("GOOGLE_API_KEY not set. AI Optimization will be skipped.")

    def ingest_node(self, state: AgentState):
        """
        Reads inventory data.
        In a real run, this might pull from a CSV file uploaded by the user.
        """
        if not state.get('inventory_items'):
             state['logs'].append("No inventory items in input.")
        return {"logs": ["Ingestion Step Complete"]}

    def optimize_node(self, state: AgentState):
        """
        Enhances product data using Gemini.
        """
        products = state.get('inventory_items', [])
        optimized = []

        if not self.llm:
            return {"processed_products": products, "logs": ["Optimization Skipped (No API Key)"]}

        parser = JsonOutputParser()
        prompt = PromptTemplate(
            template="You are an expert e-commerce copywriter. Optimize the following product data for SEO and high conversion on Amazon and Shopify.\nInput: {product}\nReturn ONLY a JSON object with keys: title, description, keywords (list).",
            input_variables=["product"],
        )
        chain = prompt | self.llm | parser

        for p in products:
            try:
                res = chain.invoke({"product": p})
                p['title'] = res.get('title', p.get('title'))
                p['description'] = res.get('description', p.get('description'))
                p['tags'] = res.get('keywords', p.get('tags', []))
                optimized.append(p)
            except Exception as e:
                logger.error("Optimization failed for product", sku=p.get('sku'), error=str(e))
                optimized.append(p)

        return {"processed_products": optimized, "logs": ["Optimization Complete"]}

    def post_node(self, state: AgentState):
        """
        Distributes products to marketplaces.
        NOW CONNECTED TO SERVICE LAYER AND PERSISTS OPTIMIZATION.
        """
        db = SessionLocal()
        service = ServiceLayer(db)

        products = state.get('processed_products', [])
        platforms = state.get('platforms_to_target', [])

        logs = []
        for p in products:
            sku = p.get('sku')
            if sku:
                # 1. Persist the Optimized Content to DB
                try:
                    product_db = db.query(Product).filter(Product.sku == sku).first()
                    if product_db:
                        product_db.title = p.get('title', product_db.title)
                        product_db.description = p.get('description', product_db.description)
                        if p.get('tags'):
                            product_db.tags = p.get('tags')
                        db.commit()
                        logger.info("Persisted AI optimization", sku=sku)
                except Exception as e:
                     logger.error("Failed to persist optimization", sku=sku, error=str(e))
                     db.rollback()

                # 2. Publish
                if platforms:
                    service.publish_product(sku, platforms)
                    logs.append(f"Published {sku} to {platforms}")

        db.close()
        return {"logs": logs}

    def report_node(self, state: AgentState):
        """
        Finalizes the run.
        """
        return {"logs": ["Run Finished"]}

# Initialize global instance
agent_system = SupervisorAgent()

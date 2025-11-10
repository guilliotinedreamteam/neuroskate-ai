"""FastAPI main application entry point"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router as api_router
from app.config import settings
from app.database import engine, Base
from app.cv.manager import CVManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global CV manager instance
cv_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global cv_manager
    
    # Startup
    logger.info("Starting NeuroSkate AI...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")
    
    # Initialize CV manager
    cv_manager = CVManager()
    await cv_manager.initialize()
    logger.info("Computer Vision engine initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NeuroSkate AI...")
    if cv_manager:
        await cv_manager.shutdown()


app = FastAPI(
    title="NeuroSkate AI",
    description="AI-powered skateboarding trick analyzer",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "NeuroSkate AI",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "api": "/api",
            "health": "/api/health"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "cv_engine": cv_manager.is_ready() if cv_manager else False,
        "database": "connected"
    }


@app.websocket("/ws/analyze")
async def websocket_analyze(websocket: WebSocket):
    """WebSocket endpoint for real-time analysis"""
    await websocket.accept()
    
    try:
        while True:
            # Receive frame data
            data = await websocket.receive_bytes()
            
            # Process frame through CV engine
            if cv_manager:
                result = await cv_manager.analyze_frame(data)
                await websocket.send_json(result)
            else:
                await websocket.send_json({"error": "CV engine not ready"})
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
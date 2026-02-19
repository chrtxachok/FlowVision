from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from api.routes import router as api_router
from api.dependencies import get_settings
from monitoring.metrics import setup_metrics
from monitoring.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for FastAPI application"""
    # Startup
    logger.info("Starting OCR Service...")
    setup_logging()
    setup_metrics(app)
    
    # Load ML models
    from ocr.pipeline import LayoutLMPipeline
    app.state.pipeline = LayoutLMPipeline(
        model_path=app.state.settings.LAYOUTLM_MODEL_PATH,
        device=app.state.settings.DEVICE
    )
    app.state.pipeline.load_models()
    
    logger.info("OCR Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down OCR Service...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="Transport Documents OCR Service",
        description="Microservice for OCR processing of transport waybills",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "ocr-service",
            "models_loaded": hasattr(app.state, 'pipeline') and app.state.pipeline.is_loaded
        }
    
    # Error handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc)}
        )
    
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    from api.dependencies import get_settings
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS
    )
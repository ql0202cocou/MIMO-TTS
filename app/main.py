"""FastAPI application entry point for MIMO-TTS Legado Bridge."""

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.tts import router as tts_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="MIMO-TTS Legado Bridge",
    description="中间件服务，将 Legado 的自定义 TTS 朗读请求转发到小米 MIMO-TTS v2.5 API",
    version="2.5.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(tts_router)


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("=" * 60)
    logger.info("MIMO-TTS Legado Bridge starting...")
    logger.info(f"API Base URL: {settings.MIMO_TTS_API_BASE_URL}")
    logger.info(f"Default Voice: {settings.MIMO_TTS_DEFAULT_VOICE}")
    logger.info(f"Default Model: {settings.MIMO_TTS_MODEL}")
    logger.info(f"Output Format: {settings.OUTPUT_AUDIO_FORMAT}")
    logger.info(f"Max Text Length: {settings.MIMO_TTS_MAX_TEXT_LENGTH}")

    if not settings.MIMO_TTS_API_KEY:
        logger.warning("⚠️  MIMO_TTS_API_KEY is not configured! API calls will fail.")
    else:
        logger.info("✅ MIMO_TTS_API_KEY is configured.")

    logger.info(f"Server listening on {settings.SERVER_HOST}:{settings.SERVER_PORT}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("MIMO-TTS Legado Bridge shutting down...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=False,
    )
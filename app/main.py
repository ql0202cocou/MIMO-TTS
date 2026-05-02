"""FastAPI application entry point for MIMO-TTS Legado Bridge."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, VERSION, CONTENT_TYPE_MAP
from app.routers.tts import router as tts_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager (startup + shutdown)."""
    from app.services.tts_service import tts_service

    # Startup
    logger.info("=" * 60)
    logger.info("MIMO-TTS Legado Bridge starting...")
    logger.info(f"API Base URL: {settings.MIMO_TTS_API_BASE_URL}")
    logger.info(f"Default Voice: {settings.MIMO_TTS_DEFAULT_VOICE}")
    logger.info(f"Default Model: {settings.MIMO_TTS_MODEL}")
    logger.info(f"Output Format: {settings.OUTPUT_AUDIO_FORMAT}")
    logger.info(f"Max Text Length: {settings.MIMO_TTS_MAX_TEXT_LENGTH}")

    if not settings.MIMO_TTS_API_KEY:
        logger.warning("MIMO_TTS_API_KEY is not configured! API calls will fail.")
    else:
        logger.info("MIMO_TTS_API_KEY is configured.")

    logger.info(f"Server listening on {settings.SERVER_HOST}:{settings.SERVER_PORT}")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("MIMO-TTS Legado Bridge shutting down...")
    await tts_service.close()
    logger.info("Shutdown complete.")


# Create FastAPI application
app = FastAPI(
    title="MIMO-TTS Legado Bridge",
    description="中间件服务，将 Legado 的自定义 TTS 朗读请求转发到小米 MIMO-TTS v2.5 API",
    version=VERSION,
    lifespan=lifespan,
)

# CORS configuration
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(tts_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=False,
    )

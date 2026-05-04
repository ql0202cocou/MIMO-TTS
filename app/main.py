"""FastAPI application entry point for MIMO-TTS Legado Bridge."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings, VERSION, CONTENT_TYPE_MAP
from app.routers.tts import router as tts_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])


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
    logger.info(f"Rate Limit: {settings.RATE_LIMIT}")
    logger.info(f"Max Request Size: {settings.MAX_REQUEST_SIZE} bytes")

    if not settings.MIMO_TTS_API_KEY:
        logger.warning("MIMO_TTS_API_KEY is not configured! API calls will fail.")
    else:
        logger.info("MIMO_TTS_API_KEY is configured.")

    if not settings.API_KEY:
        logger.warning(
            "API_KEY is not configured! Service is open to all. "
            "Set API_KEY in production environment."
        )
    else:
        logger.info("API_KEY is configured. Authentication enabled.")

    if settings.CORS_ORIGINS.strip() == "*":
        logger.warning(
            "CORS_ORIGINS is set to '*' (allow all). "
            "This is INSECURE for production! "
            "Please set specific origins in production environment."
        )

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

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", settings.API_KEY_HEADER],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


# Register routes
app.include_router(tts_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=False,
        limit_max_request_size=settings.MAX_REQUEST_SIZE,
    )

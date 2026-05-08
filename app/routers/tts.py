"""TTS route handlers for Legado HTTP TTS engine integration."""

import hmac
import logging
import re
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import Response
from app.config import settings, VERSION, SPEED_DEFAULT, SPEED_MIN, SPEED_MAX, CONTENT_TYPE_MAP, limiter
from app.models.schemas import TTSRequest, VoiceInfo, HealthResponse
from app.services.tts_service import tts_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tts"])


def verify_api_key(request: Request) -> None:
    """Verify API key if configured using constant-time comparison."""
    if not settings.API_KEY:
        return  # No authentication required
    
    api_key = request.headers.get(settings.API_KEY_HEADER)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def sanitize_text(text: str) -> str:
    """Sanitize input text to prevent prompt injection and other attacks."""
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Remove potential prompt injection patterns
    # Block common injection markers used in LLM prompts
    injection_patterns = [
        (r'(?i)\b(system|assistant|user)\s*:', "role_markers"),
        (r'(?i)\b(ignore|forget|disregard)\s+(previous|above|all)\b', "instruction_override"),
        (r'(?i)\b(you are now|act as|pretend to be|roleplay as)\b', "role_hijacking"),
        (r'(?i)\b(instruct|prompt|command)\s*:', "instruction_markers"),
        (r'```\s*(system|assistant|user)', "code_block_injection"),
        (r'<\|(system|assistant|user)\|>', "special_token_injection"),
    ]
    for pattern, pattern_name in injection_patterns:
        if re.search(pattern, text):
            logger.warning(f"Prompt injection detected: pattern={pattern_name}, text_preview={text[:100]!r}")
        text = re.sub(pattern, '', text)
    
    # Limit consecutive whitespace
    text = re.sub(r'\s{10,}', ' ', text)
    
    # Limit total length
    return text.strip()[:10000]


def sanitize_style(style: str) -> str:
    """Sanitize style parameter."""
    # Remove control characters
    style = re.sub(r'[\x00-\x1f\x7f]', '', style)
    # Only allow common style characters
    style = re.sub(r'[^\w\s，、。！？：；""''（）\-\+]', '', style)
    return style.strip()[:200]  # Limit length


def sanitize_voice(voice: str) -> str:
    """Sanitize voice parameter."""
    # Remove control characters and special chars
    voice = re.sub(r'[^\w\-]', '', voice)
    return voice.strip()[:50]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点."""
    return HealthResponse(
        status="ok",
        version=VERSION,
    )


@router.get("/voices", response_model=list[VoiceInfo])
async def get_voices(request: Request, api_key: None = Depends(verify_api_key)):
    """获取可用音色列表."""
    voices = tts_service.get_voices()
    return [VoiceInfo(**v) for v in voices]


async def _handle_speak(text: str, speed: int, voice: str | None, style: str | None) -> Response:
    """Shared logic for GET and POST /speak endpoints."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")

    try:
        logger.info(f"/speak: text_length={len(text)}, speed={speed}, voice={voice}")

        audio_data = await tts_service.synthesize_long_text(
            text=text,
            voice=voice,
            style_hint=style,
            speed=speed,
        )

        content_type = CONTENT_TYPE_MAP.get(tts_service.output_format, "audio/wav")
        return Response(content=audio_data, media_type=content_type)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS synthesis failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="语音合成失败，请稍后重试")


@router.get("/speak")
@limiter.limit(settings.RATE_LIMIT)
async def speak_get(
    request: Request,
    text: str = Query(..., description="要朗读的文本（URL 编码）"),
    speed: int = Query(default=SPEED_DEFAULT, ge=SPEED_MIN, le=SPEED_MAX, description="朗读速度"),
    voice: str = Query(default=None, description="音色选择"),
    style: str = Query(default=None, description="风格标签"),
    api_key: None = Depends(verify_api_key),
):
    """GET 方式朗读文本，返回音频二进制数据."""
    sanitized_text = sanitize_text(unquote(text))
    sanitized_voice = sanitize_voice(voice) if voice else None
    sanitized_style = sanitize_style(style) if style else None
    return await _handle_speak(sanitized_text, speed, sanitized_voice, sanitized_style)


@router.post("/speak")
@limiter.limit(settings.RATE_LIMIT)
async def speak_post(request: Request, api_key: None = Depends(verify_api_key)):
    """POST 方式朗读文本，返回音频二进制数据."""

    # Parse request body manually for rate limiting
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON")
    
    # Validate with Pydantic
    try:
        tts_request = TTSRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    sanitized_text = sanitize_text(tts_request.text)
    sanitized_voice = sanitize_voice(tts_request.voice) if tts_request.voice else None
    sanitized_style = sanitize_style(tts_request.style) if tts_request.style else None
    return await _handle_speak(sanitized_text, tts_request.speed, sanitized_voice, sanitized_style)

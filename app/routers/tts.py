"""TTS route handlers for Legado HTTP TTS engine integration."""

import logging
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.config import settings, VERSION, SPEED_DEFAULT, SPEED_MIN, SPEED_MAX, CONTENT_TYPE_MAP
from app.models.schemas import TTSRequest, VoiceInfo, HealthResponse
from app.services.tts_service import tts_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tts"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点."""
    return HealthResponse(
        status="ok",
        version=VERSION,
        api_configured=tts_service.is_configured(),
    )


@router.get("/voices", response_model=list[VoiceInfo])
async def get_voices():
    """获取可用音色列表."""
    voices = tts_service.get_voices()
    return [VoiceInfo(**v) for v in voices]


async def _handle_speak(text: str, speed: int, voice: str | None, style: str | None) -> Response:
    """Shared logic for GET and POST /speak endpoints."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")

    try:
        logger.info(f"/speak: text={text[:50]}..., speed={speed}, voice={voice}, style={style}")

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
        logger.error(f"TTS synthesis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="语音合成失败，请稍后重试")


@router.get("/speak")
async def speak_get(
    text: str = Query(..., description="要朗读的文本（URL 编码）"),
    speed: int = Query(default=SPEED_DEFAULT, ge=SPEED_MIN, le=SPEED_MAX, description="朗读速度"),
    voice: str = Query(default=None, description="音色选择"),
    style: str = Query(default=None, description="风格标签"),
):
    """GET 方式朗读文本，返回音频二进制数据."""
    return await _handle_speak(unquote(text), speed, voice, style)


@router.post("/speak")
async def speak_post(request: TTSRequest):
    """POST 方式朗读文本，返回音频二进制数据."""
    return await _handle_speak(request.text, request.speed, request.voice, request.style)

"""TTS route handlers for Legado HTTP TTS engine integration."""

import logging
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.models.schemas import TTSRequest, VoiceInfo, HealthResponse
from app.services.tts_service import tts_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tts"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点."""
    return HealthResponse(
        status="ok",
        version="2.5.0",
        api_configured=tts_service.is_configured(),
    )


@router.get("/voices", response_model=list[VoiceInfo])
async def get_voices():
    """获取可用音色列表."""
    voices = tts_service.get_voices()
    return [VoiceInfo(**v) for v in voices]


@router.get("/speak")
async def speak_get(
    text: str = Query(..., description="要朗读的文本（URL 编码）"),
    speed: int = Query(default=30, ge=5, le=50, description="朗读速度，范围 5-50"),
    voice: str = Query(default=None, description="音色选择"),
    style: str = Query(default=None, description="风格标签"),
):
    """GET 方式朗读文本，返回音频二进制数据.

    此端点兼容 Legado HTTP TTS 引擎的 GET 请求格式。
    """
    # URL 解码文本
    decoded_text = unquote(text)

    if not decoded_text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")

    try:
        logger.info(f"GET /speak: text={decoded_text[:50]}..., speed={speed}, voice={voice}, style={style}")

        audio_data = await tts_service.synthesize_long_text(
            text=decoded_text,
            voice=voice,
            style_hint=style,
            speed=speed,
        )

        content_type = "audio/wav" if tts_service.output_format == "wav" else "audio/mpeg"
        return Response(content=audio_data, media_type=content_type)

    except Exception as e:
        logger.error(f"TTS synthesis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")


@router.post("/speak")
async def speak_post(request: TTSRequest):
    """POST 方式朗读文本，返回音频二进制数据.

    此端点兼容 Legado HTTP TTS 引擎的 POST 请求格式。
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")

    try:
        logger.info(
            f"POST /speak: text={request.text[:50]}..., "
            f"speed={request.speed}, voice={request.voice}, style={request.style}"
        )

        audio_data = await tts_service.synthesize_long_text(
            text=request.text,
            voice=request.voice,
            style_hint=request.style,
            speed=request.speed,
        )

        content_type = "audio/wav" if tts_service.output_format == "wav" else "audio/mpeg"
        return Response(content=audio_data, media_type=content_type)

    except Exception as e:
        logger.error(f"TTS synthesis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")

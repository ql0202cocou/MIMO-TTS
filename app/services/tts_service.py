"""MIMO-TTS API call service using async OpenAI SDK."""

import asyncio
import base64
import io
import logging
import wave
from typing import Optional

from openai import AsyncOpenAI
from openai import (
    APITimeoutError,
    APIConnectionError,
    APIStatusError,
    RateLimitError,
)

from app.config import (
    settings,
    MIN_SEGMENT_LENGTH,
    MIN_COMMA_SEGMENT_LENGTH,
    WAV_HEADER_SIZE,
)

logger = logging.getLogger(__name__)

# Built-in voice list (tuple of dicts for immutability)
BUILTIN_VOICES = (
    {"name": "MiMo-默认", "voice_id": "mimo_default", "language": "中文", "gender": "-"},
    {"name": "晓晓", "voice_id": "晓晓", "language": "中文", "gender": "女"},
    {"name": "晓伊", "voice_id": "晓伊", "language": "中文", "gender": "女"},
    {"name": "云阳", "voice_id": "云阳", "language": "中文", "gender": "男"},
    {"name": "云逸", "voice_id": "云逸", "language": "中文", "gender": "男"},
    {"name": "Mia", "voice_id": "Mia", "language": "英文", "gender": "女"},
    {"name": "Chloe", "voice_id": "Chloe", "language": "英文", "gender": "女"},
    {"name": "Milo", "voice_id": "Milo", "language": "英文", "gender": "男"},
    {"name": "Dean", "voice_id": "Dean", "language": "英文", "gender": "男"},
)

VALID_VOICE_IDS = {v["voice_id"] for v in BUILTIN_VOICES}

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1.0

# Retryable exception types
RETRYABLE_ERRORS = (APITimeoutError, APIConnectionError, RateLimitError)


def _is_retryable(exc: Exception) -> bool:
    """Check if an exception is retryable (transient network/server errors)."""
    if isinstance(exc, RETRYABLE_ERRORS):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code >= 500:
        return True
    return False


def speed_to_hint(speed: int) -> str:
    """将 Legado 的 speakSpeed (5-50) 转换为 MIMO 风格指令."""
    if speed <= 15:
        return "语速很慢，缓慢朗读"
    elif speed <= 25:
        return "语速较慢，从容朗读"
    elif speed <= 35:
        return "语速适中"
    elif speed <= 45:
        return "语速较快，紧凑朗读"
    else:
        return "语速很快，快速朗读"


class TTSService:
    """MIMO-TTS API service for text-to-speech synthesis."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.MIMO_TTS_API_KEY,
            base_url=settings.MIMO_TTS_API_BASE_URL,
            timeout=settings.MIMO_TTS_TIMEOUT,
        )
        self.default_voice = settings.MIMO_TTS_DEFAULT_VOICE
        self.default_model = settings.MIMO_TTS_MODEL
        self.default_style = settings.MIMO_TTS_DEFAULT_STYLE
        self.max_text_length = settings.MIMO_TTS_MAX_TEXT_LENGTH
        self.output_format = settings.OUTPUT_AUDIO_FORMAT

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.close()

    def validate_voice(self, voice: Optional[str]) -> str:
        """校验音色参数，无效值回退到默认音色."""
        if voice is None:
            return self.default_voice
        if voice not in VALID_VOICE_IDS:
            logger.warning(f"Invalid voice '{voice}', falling back to default '{self.default_voice}'")
            return self.default_voice
        return voice

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        style_hint: Optional[str] = None,
        speed: Optional[int] = None,
        audio_format: Optional[str] = None,
    ) -> bytes:
        """将文本转换为音频.

        Args:
            text: 要合成的文本
            voice: 音色名称
            style_hint: 风格指令
            speed: 朗读速度 (5-50)
            audio_format: 音频格式 (wav/pcm16)

        Returns:
            音频二进制数据

        Raises:
            RuntimeError: API 调用在所有重试后仍然失败
        """
        voice = self.validate_voice(voice)
        audio_format = audio_format or self.output_format

        # 构建风格指令
        style_parts = []
        if style_hint:
            style_parts.append(style_hint)
        if speed is not None:
            style_parts.append(speed_to_hint(speed))
        if not style_parts and self.default_style:
            style_parts.append(self.default_style)

        combined_style = "，".join(style_parts) if style_parts else None

        # 构建消息
        messages = []
        if combined_style:
            messages.append({"role": "user", "content": combined_style})
        messages.append({"role": "assistant", "content": text})

        logger.info(
            f"Calling MIMO-TTS API: model={self.default_model}, "
            f"voice={voice}, format={audio_format}, "
            f"style={combined_style}, text_length={len(text)}"
        )

        # 带重试的 API 调用
        last_exception: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                completion = await self.client.chat.completions.create(
                    model=self.default_model,
                    messages=messages,
                    audio={"format": audio_format, "voice": voice},
                )

                # Null-safety checks on API response
                if not completion.choices:
                    raise RuntimeError("API returned empty choices list")

                message = completion.choices[0].message
                if message.audio is None or not message.audio.data:
                    raise RuntimeError("API returned no audio data")

                audio_bytes = base64.b64decode(message.audio.data)

                logger.info(f"MIMO-TTS API response received, audio size: {len(audio_bytes)} bytes")
                return audio_bytes

            except Exception as e:
                last_exception = e

                if not _is_retryable(e):
                    logger.error(f"Non-retryable API error: {e}")
                    raise

                if attempt < MAX_RETRIES:
                    wait = RETRY_DELAY * attempt
                    logger.warning(f"API call failed (attempt {attempt}/{MAX_RETRIES}): {e}, retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"API call failed after {MAX_RETRIES} attempts: {e}")

        raise RuntimeError(f"TTS synthesis failed after {MAX_RETRIES} retries") from last_exception

    async def synthesize_long_text(
        self,
        text: str,
        voice: Optional[str] = None,
        style_hint: Optional[str] = None,
        speed: Optional[int] = None,
        audio_format: Optional[str] = None,
    ) -> bytes:
        """合成长文本，自动分段处理.

        对于超过 max_text_length 的文本，按标点符号分段后分别合成并拼接。
        """
        if len(text) <= self.max_text_length:
            return await self.synthesize(text, voice, style_hint, speed, audio_format)

        # 分段处理
        segments = self._split_text(text)
        logger.info(f"Long text split into {len(segments)} segments")

        audio_format = audio_format or self.output_format

        audio_parts = []
        for i, segment in enumerate(segments):
            logger.info(f"Synthesizing segment {i + 1}/{len(segments)}, length: {len(segment)}")
            audio_data = await self.synthesize(segment, voice, style_hint, speed, audio_format)
            audio_parts.append(audio_data)

        # 拼接音频
        if audio_format == "wav":
            return self._concatenate_wav(audio_parts)
        else:
            # PCM/MP3 等格式直接拼接字节
            return b"".join(audio_parts)

    def _split_text(self, text: str) -> list[str]:
        """按标点符号将长文本分段，带兜底截断."""
        max_len = self.max_text_length
        delimiters = {"。", "！", "？", "；", "\n", ".", "!", "?", ";"}
        segments = []
        parts: list[str] = []

        for char in text:
            parts.append(char)
            # 在标点处切分（段落长度 >= MIN_SEGMENT_LENGTH 时）或强制截断（达到上限时）
            if char in delimiters and len(parts) >= MIN_SEGMENT_LENGTH:
                segments.append("".join(parts).strip())
                parts = []
            elif len(parts) >= max_len:
                segments.append("".join(parts).strip())
                parts = []

        # 处理剩余文本
        if parts:
            remaining = "".join(parts).strip()
            if remaining:
                if len(remaining) > max_len:
                    sub_segments = self._split_by_comma(remaining)
                    segments.extend(sub_segments)
                else:
                    segments.append(remaining)

        # 合并过短的段落
        merged = []
        buffer = ""
        for seg in segments:
            if len(buffer) + len(seg) <= max_len:
                buffer += seg
            else:
                if buffer:
                    merged.append(buffer)
                if len(seg) > max_len:
                    for i in range(0, len(seg), max_len):
                        merged.append(seg[i:i + max_len])
                else:
                    buffer = seg
        if buffer:
            merged.append(buffer)

        return merged if merged else [text[:max_len]]

    def _split_by_comma(self, text: str) -> list[str]:
        """按逗号分割文本，带兜底截断."""
        max_len = self.max_text_length
        delimiters = {"，", ",", "、", "：", ":"}
        segments = []
        parts: list[str] = []

        for char in text:
            parts.append(char)
            if char in delimiters and len(parts) >= MIN_COMMA_SEGMENT_LENGTH:
                segments.append("".join(parts).strip())
                parts = []
            elif len(parts) >= max_len:
                segments.append("".join(parts).strip())
                parts = []

        if parts:
            remaining = "".join(parts).strip()
            if remaining:
                segments.append(remaining)

        return segments

    def _concatenate_wav(self, wav_parts: list[bytes]) -> bytes:
        """拼接多个 WAV 音频文件.

        使用 wave 标准库正确解析 WAV 头部，提取音频参数和数据后拼接。
        校验所有片段的音频参数一致性。
        """
        if len(wav_parts) == 1:
            return wav_parts[0]

        # 从第一个 WAV 文件读取音频参数
        first_wav = io.BytesIO(wav_parts[0])
        with wave.open(first_wav, "rb") as w:
            params = w.getparams()
            first_data = w.readframes(w.getnframes())

        # 收集所有音频数据并校验参数一致性
        all_data = [first_data]
        for idx, part in enumerate(wav_parts[1:], start=2):
            part_wav = io.BytesIO(part)
            try:
                with wave.open(part_wav, "rb") as w:
                    part_params = w.getparams()
                    if (
                        part_params.nchannels != params.nchannels
                        or part_params.sampwidth != params.sampwidth
                        or part_params.framerate != params.framerate
                    ):
                        raise RuntimeError(
                            f"WAV part {idx} has different audio params "
                            f"({part_params.nchannels}ch/{part_params.framerate}Hz/{part_params.sampwidth}B) "
                            f"vs part 1 ({params.nchannels}ch/{params.framerate}Hz/{params.sampwidth}B)"
                        )
                    all_data.append(w.readframes(w.getnframes()))
            except RuntimeError:
                raise
            except Exception as e:
                logger.warning(f"Failed to parse WAV part {idx}: {e}")
                raise RuntimeError(f"WAV part {idx} is corrupted and cannot be processed") from e

        combined_data = b"".join(all_data)

        # 写入新的 WAV 文件
        output = io.BytesIO()
        with wave.open(output, "wb") as out_wav:
            out_wav.setparams(params)
            out_wav.writeframes(combined_data)

        return output.getvalue()

    def get_voices(self) -> tuple[dict, ...]:
        """获取可用音色列表."""
        return BUILTIN_VOICES

    def is_configured(self) -> bool:
        """检查 API Key 是否已配置."""
        return bool(settings.MIMO_TTS_API_KEY)


# Global service instance
tts_service = TTSService()

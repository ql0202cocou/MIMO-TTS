"""MIMO-TTS API call service using OpenAI SDK."""

import base64
import logging
from typing import Optional

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# Built-in voice list
BUILTIN_VOICES = [
    {"name": "MiMo-默认", "voice_id": "mimo_default", "language": "中文", "gender": "-"},
    {"name": "晓晓", "voice_id": "晓晓", "language": "中文", "gender": "女"},
    {"name": "晓伊", "voice_id": "晓伊", "language": "中文", "gender": "女"},
    {"name": "云阳", "voice_id": "云阳", "language": "中文", "gender": "男"},
    {"name": "云逸", "voice_id": "云逸", "language": "中文", "gender": "男"},
    {"name": "Mia", "voice_id": "Mia", "language": "英文", "gender": "女"},
    {"name": "Chloe", "voice_id": "Chloe", "language": "英文", "gender": "女"},
    {"name": "Milo", "voice_id": "Milo", "language": "英文", "gender": "男"},
    {"name": "Dean", "voice_id": "Dean", "language": "英文", "gender": "男"},
]


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

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.MIMO_TTS_API_KEY,
            base_url=settings.MIMO_TTS_API_BASE_URL,
            timeout=settings.MIMO_TTS_TIMEOUT,
        )
        self.default_voice = settings.MIMO_TTS_DEFAULT_VOICE
        self.default_model = settings.MIMO_TTS_MODEL
        self.default_style = settings.MIMO_TTS_DEFAULT_STYLE
        self.max_text_length = settings.MIMO_TTS_MAX_TEXT_LENGTH
        self.output_format = settings.OUTPUT_AUDIO_FORMAT

    def synthesize(
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
        """
        voice = voice or self.default_voice
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

        # 用户风格指令（可选）
        if combined_style:
            messages.append({"role": "user", "content": combined_style})

        # 合成文本（必须放在 assistant 角色）
        messages.append({"role": "assistant", "content": text})

        logger.info(
            f"Calling MIMO-TTS API: model={self.default_model}, "
            f"voice={voice}, format={audio_format}, "
            f"style={combined_style}, text_length={len(text)}"
        )

        completion = self.client.chat.completions.create(
            model=self.default_model,
            messages=messages,
            audio={"format": audio_format, "voice": voice},
        )

        message = completion.choices[0].message
        audio_bytes = base64.b64decode(message.audio.data)

        logger.info(f"MIMO-TTS API response received, audio size: {len(audio_bytes)} bytes")
        return audio_bytes

    def synthesize_long_text(
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
            return self.synthesize(text, voice, style_hint, speed, audio_format)

        # 分段处理
        segments = self._split_text(text)
        logger.info(f"Long text split into {len(segments)} segments")

        audio_parts = []
        for i, segment in enumerate(segments):
            logger.info(f"Synthesizing segment {i + 1}/{len(segments)}, length: {len(segment)}")
            audio_data = self.synthesize(segment, voice, style_hint, speed, audio_format)
            audio_parts.append(audio_data)

        # 拼接音频
        return self._concatenate_wav(audio_parts)

    def _split_text(self, text: str) -> list[str]:
        """按标点符号将长文本分段."""
        # 分割标点符号
        delimiters = ["。", "！", "？", "；", "\n", ".", "!", "?", ";"]
        segments = []
        current_segment = ""

        for char in text:
            current_segment += char
            if char in delimiters and len(current_segment) >= 50:
                segments.append(current_segment.strip())
                current_segment = ""

        # 处理剩余文本
        if current_segment.strip():
            # 如果剩余文本仍然过长，按逗号继续分割
            if len(current_segment) > self.max_text_length:
                sub_segments = self._split_by_comma(current_segment)
                segments.extend(sub_segments)
            else:
                segments.append(current_segment.strip())

        # 合并过短的段落
        merged = []
        buffer = ""
        for seg in segments:
            if len(buffer) + len(seg) <= self.max_text_length:
                buffer += seg
            else:
                if buffer:
                    merged.append(buffer)
                buffer = seg
        if buffer:
            merged.append(buffer)

        return merged if merged else [text[:self.max_text_length]]

    def _split_by_comma(self, text: str) -> list[str]:
        """按逗号分割文本."""
        delimiters = ["，", ",", "、", "：", ":"]
        segments = []
        current = ""

        for char in text:
            current += char
            if char in delimiters and len(current) >= 20:
                segments.append(current.strip())
                current = ""

        if current.strip():
            segments.append(current.strip())

        return segments

    def _concatenate_wav(self, wav_parts: list[bytes]) -> bytes:
        """拼接多个 WAV 音频文件.

        简单拼接：跳过除第一个外的 WAV 文件头，直接拼接音频数据。
        """
        if len(wav_parts) == 1:
            return wav_parts[0]

        # WAV 文件头通常是 44 字节
        header = wav_parts[0][:44]
        data_parts = []

        for part in wav_parts:
            if len(part) > 44:
                data_parts.append(part[44:])
            else:
                data_parts.append(part)

        combined_data = b"".join(data_parts)

        # 更新 WAV 头中的文件大小字段
        header = bytearray(header)
        file_size = len(combined_data) + 36
        header[4:8] = file_size.to_bytes(4, "little")
        data_size = len(combined_data)
        header[40:44] = data_size.to_bytes(4, "little")

        return bytes(header) + combined_data

    def get_voices(self) -> list[dict]:
        """获取可用音色列表."""
        return BUILTIN_VOICES

    def is_configured(self) -> bool:
        """检查 API Key 是否已配置."""
        return bool(settings.MIMO_TTS_API_KEY)


# Global service instance
tts_service = TTSService()
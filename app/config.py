"""Configuration management for MIMO-TTS Legado Bridge."""

from typing import Literal

from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv(override=False)

VERSION = "0.1.0"

# Speed range constants
SPEED_MIN = 5
SPEED_MAX = 50
SPEED_DEFAULT = 30

# Split thresholds
MIN_SEGMENT_LENGTH = 50
MIN_COMMA_SEGMENT_LENGTH = 20
WAV_HEADER_SIZE = 44

# Supported audio formats
AudioFormat = Literal["wav", "mp3", "pcm16"]

# Content type mapping
CONTENT_TYPE_MAP = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "pcm16": "audio/L16",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MIMO-TTS API configuration
    MIMO_TTS_API_BASE_URL: str = Field(
        default="https://api.xiaomimimo.com/v1",
        description="MIMO-TTS API 基础地址",
    )
    MIMO_TTS_API_KEY: str = Field(default="", description="MIMO-TTS API Key")
    MIMO_TTS_MODEL: str = Field(default="mimo-v2.5-tts", description="模型名称")
    MIMO_TTS_DEFAULT_VOICE: str = Field(default="晓晓", description="默认音色")
    MIMO_TTS_DEFAULT_STYLE: str = Field(default="温柔，语速适中", description="默认风格指令")
    MIMO_TTS_TIMEOUT: int = Field(default=60, ge=1, description="请求超时时间（秒）")
    MIMO_TTS_MAX_TEXT_LENGTH: int = Field(default=5000, ge=100, description="单次最大文本长度")

    # Output configuration
    OUTPUT_AUDIO_FORMAT: AudioFormat = Field(default="wav", description="输出音频格式")

    # Server configuration
    SERVER_HOST: str = Field(default="0.0.0.0", description="服务监听地址")
    SERVER_PORT: int = Field(default=9880, description="服务监听端口")

    # CORS configuration
    CORS_ORIGINS: str = Field(default="*", description="CORS 允许的来源，逗号分隔")

    # Log level
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()

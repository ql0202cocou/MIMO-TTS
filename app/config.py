"""Configuration management for MIMO-TTS Legado Bridge."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # MIMO-TTS API configuration
    MIMO_TTS_API_BASE_URL: str = os.getenv(
        "MIMO_TTS_API_BASE_URL", "https://api.xiaomimimo.com/v1"
    )
    MIMO_TTS_API_KEY: str = os.getenv("MIMO_TTS_API_KEY", "")
    MIMO_TTS_MODEL: str = os.getenv("MIMO_TTS_MODEL", "mimo-v2.5-tts")
    MIMO_TTS_DEFAULT_VOICE: str = os.getenv("MIMO_TTS_DEFAULT_VOICE", "晓晓")
    MIMO_TTS_DEFAULT_STYLE: str = os.getenv("MIMO_TTS_DEFAULT_STYLE", "温柔，语速适中")
    MIMO_TTS_TIMEOUT: int = int(os.getenv("MIMO_TTS_TIMEOUT", "60"))
    MIMO_TTS_MAX_TEXT_LENGTH: int = int(os.getenv("MIMO_TTS_MAX_TEXT_LENGTH", "5000"))

    # Output configuration
    OUTPUT_AUDIO_FORMAT: str = os.getenv("OUTPUT_AUDIO_FORMAT", "wav")

    # Server configuration
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "9880"))


settings = Settings()
"""Pydantic data models for request/response validation."""

from typing import Optional
from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    """TTS request data model."""

    text: str = Field(..., description="要朗读的文本内容")
    speed: Optional[int] = Field(default=30, ge=5, le=50, description="朗读速度，范围 5-50")
    voice: Optional[str] = Field(default=None, description="音色选择（晓晓/云阳/Chloe 等）")
    style: Optional[str] = Field(default=None, description="风格标签（如'温柔'、'开心'）")


class VoiceInfo(BaseModel):
    """Voice information model."""

    name: str = Field(..., description="音色名称")
    voice_id: str = Field(..., description="音色 ID")
    language: str = Field(..., description="支持的语言")
    gender: str = Field(..., description="性别")


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(default="ok", description="服务状态")
    version: str = Field(default="2.5.0", description="MIMO-TTS 版本")
    api_configured: bool = Field(default=False, description="API Key 是否已配置")


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str = Field(..., description="错误详情")
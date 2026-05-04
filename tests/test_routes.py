"""Tests for API routes."""

import pytest
from unittest.mock import patch, AsyncMock

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import VERSION


@pytest.fixture
def client():
    """Create an async test client."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.anyio
async def test_health_check(client):
    async with client as c:
        resp = await c.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == VERSION
        assert "api_configured" not in data


@pytest.mark.anyio
async def test_get_voices(client):
    async with client as c:
        resp = await c.get("/voices")
        assert resp.status_code == 200
        voices = resp.json()
        assert isinstance(voices, list)
        assert len(voices) > 0
        assert "name" in voices[0]
        assert "voice_id" in voices[0]
        assert "language" in voices[0]
        assert "gender" in voices[0]


@pytest.mark.anyio
async def test_speak_get_empty_text(client):
    async with client as c:
        resp = await c.get("/speak", params={"text": "  "})
        assert resp.status_code == 400
        assert "文本不能为空" in resp.json()["detail"]


@pytest.mark.anyio
async def test_speak_post_empty_text(client):
    async with client as c:
        resp = await c.post("/speak", json={"text": "  "})
        assert resp.status_code == 400
        assert "文本不能为空" in resp.json()["detail"]


@pytest.mark.anyio
async def test_speak_post_invalid_speed(client):
    async with client as c:
        resp = await c.post("/speak", json={"text": "hello", "speed": 100})
        assert resp.status_code == 422


@pytest.mark.anyio
async def test_speak_get_success(client):
    mock_audio = b"RIFF" + b"\x00" * 40

    with patch(
        "app.services.tts_service.TTSService.synthesize_long_text",
        new_callable=AsyncMock,
        return_value=mock_audio,
    ):
        async with client as c:
            resp = await c.get("/speak", params={"text": "你好", "speed": 30})
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "audio/wav"
            assert resp.content == mock_audio


@pytest.mark.anyio
async def test_speak_post_success(client):
    mock_audio = b"RIFF" + b"\x00" * 40

    with patch(
        "app.services.tts_service.TTSService.synthesize_long_text",
        new_callable=AsyncMock,
        return_value=mock_audio,
    ):
        async with client as c:
            resp = await c.post("/speak", json={"text": "你好", "speed": 30})
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "audio/wav"
            assert resp.content == mock_audio


@pytest.mark.anyio
async def test_speak_post_500_no_detail_leak(client):
    """Verify internal error details are not leaked to the client."""
    with patch(
        "app.services.tts_service.TTSService.synthesize_long_text",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Internal secret info: api_key=sk-xxx"),
    ):
        async with client as c:
            resp = await c.post("/speak", json={"text": "你好"})
            assert resp.status_code == 500
            detail = resp.json()["detail"]
            assert "sk-xxx" not in detail
            assert "secret" not in detail
            assert "语音合成失败" in detail


@pytest.mark.anyio
async def test_security_headers(client):
    """Verify security headers are present."""
    async with client as c:
        resp = await c.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

"""Tests for API routes."""

import pytest
from unittest.mock import patch, AsyncMock

from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "2.5.0"
        assert "api_configured" in data


@pytest.mark.anyio
async def test_get_voices():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/voices")
        assert resp.status_code == 200
        voices = resp.json()
        assert isinstance(voices, list)
        assert len(voices) > 0
        # Check first voice has required fields
        assert "name" in voices[0]
        assert "voice_id" in voices[0]
        assert "language" in voices[0]
        assert "gender" in voices[0]


@pytest.mark.anyio
async def test_speak_get_empty_text():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/speak", params={"text": "  "})
        assert resp.status_code == 400
        assert "文本不能为空" in resp.json()["detail"]


@pytest.mark.anyio
async def test_speak_post_empty_text():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/speak", json={"text": "  "})
        assert resp.status_code == 400
        assert "文本不能为空" in resp.json()["detail"]


@pytest.mark.anyio
async def test_speak_post_invalid_speed():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/speak", json={"text": "hello", "speed": 100})
        assert resp.status_code == 422  # Validation error


@pytest.mark.anyio
async def test_speak_get_success():
    mock_audio = b"RIFF" + b"\x00" * 40  # Fake WAV header

    with patch(
        "app.services.tts_service.TTSService.synthesize_long_text",
        new_callable=AsyncMock,
        return_value=mock_audio,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/speak", params={"text": "你好", "speed": 30})
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "audio/wav"
            assert resp.content == mock_audio


@pytest.mark.anyio
async def test_speak_post_success():
    mock_audio = b"RIFF" + b"\x00" * 40

    with patch(
        "app.services.tts_service.TTSService.synthesize_long_text",
        new_callable=AsyncMock,
        return_value=mock_audio,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/speak", json={"text": "你好", "speed": 30})
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "audio/wav"
            assert resp.content == mock_audio

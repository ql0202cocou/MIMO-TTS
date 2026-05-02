"""Tests for TTS service logic (no API calls)."""

import io
import struct
import wave

import pytest

from app.services.tts_service import TTSService, speed_to_hint, VALID_VOICE_IDS


@pytest.fixture
def service():
    """Create a TTSService instance for testing."""
    return TTSService()


def _make_wav_bytes(num_frames=1000, sample_rate=24000, num_channels=1, sample_width=2):
    """Helper to create valid WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(num_channels)
        w.setsampwidth(sample_width)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


class TestSpeedToHint:
    def test_very_slow(self):
        assert "很慢" in speed_to_hint(5)

    def test_slow(self):
        assert "较慢" in speed_to_hint(20)

    def test_medium(self):
        assert "适中" in speed_to_hint(30)

    def test_fast(self):
        assert "较快" in speed_to_hint(40)

    def test_very_fast(self):
        assert "很快" in speed_to_hint(50)

    def test_boundary_15(self):
        assert "很慢" in speed_to_hint(15)

    def test_boundary_16(self):
        assert "较慢" in speed_to_hint(16)

    def test_boundary_25(self):
        assert "较慢" in speed_to_hint(25)

    def test_boundary_26(self):
        assert "适中" in speed_to_hint(26)


class TestValidateVoice:
    def test_valid_voice(self, service):
        assert service.validate_voice("晓晓") == "晓晓"

    def test_valid_voice_english(self, service):
        assert service.validate_voice("Chloe") == "Chloe"

    def test_none_returns_default(self, service):
        assert service.validate_voice(None) == service.default_voice

    def test_invalid_voice_falls_back(self, service):
        assert service.validate_voice("不存在的音色") == service.default_voice

    def test_empty_string_falls_back(self, service):
        assert service.validate_voice("") == service.default_voice

    def test_all_valid_voices(self, service):
        for vid in VALID_VOICE_IDS:
            assert service.validate_voice(vid) == vid


class TestSplitText:
    def test_short_text_no_split(self, service):
        text = "这是一段短文本。"
        segments = service._split_text(text)
        assert len(segments) == 1
        assert segments[0] == text

    def test_long_text_splits_at_punctuation(self, service):
        # Create text longer than 50 chars with punctuation
        text = "这是一个测试句子。" * 20  # well over max_text_length
        service.max_text_length = 100
        segments = service._split_text(text)
        assert len(segments) > 1
        for seg in segments:
            assert len(seg) <= 100

    def test_no_punctuation_force_split(self, service):
        # Text with no punctuation at all
        text = "a" * 200
        service.max_text_length = 100
        segments = service._split_text(text)
        assert len(segments) >= 2
        for seg in segments:
            assert len(seg) <= 100

    def test_empty_after_strip(self, service):
        text = "   "
        segments = service._split_text(text)
        # Should return at least one segment
        assert len(segments) >= 1


class TestSplitByComma:
    def test_short_text_no_split(self, service):
        text = "短文本，"
        segments = service._split_by_comma(text)
        assert len(segments) == 1

    def test_no_comma_force_split(self, service):
        text = "a" * 200
        service.max_text_length = 100
        segments = service._split_by_comma(text)
        for seg in segments:
            assert len(seg) <= 100


class TestConcatenateWav:
    def test_single_wav(self, service):
        wav_bytes = _make_wav_bytes(1000)
        result = service._concatenate_wav([wav_bytes])
        assert result == wav_bytes

    def test_multiple_wav(self, service):
        wav1 = _make_wav_bytes(1000)
        wav2 = _make_wav_bytes(500)
        result = service._concatenate_wav([wav1, wav2])

        # Verify result is valid WAV
        buf = io.BytesIO(result)
        with wave.open(buf, "rb") as w:
            assert w.getnframes() == 1500
            assert w.getframerate() == 24000

    def test_concatenated_params_preserved(self, service):
        wav1 = _make_wav_bytes(1000, sample_rate=24000)
        wav2 = _make_wav_bytes(500, sample_rate=24000)
        result = service._concatenate_wav([wav1, wav2])

        buf = io.BytesIO(result)
        with wave.open(buf, "rb") as w:
            params = w.getparams()
            assert params.nchannels == 1
            assert params.sampwidth == 2
            assert params.framerate == 24000

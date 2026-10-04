import asyncio
import io
import json
import wave

import httpx
import pytest

from vnizer import services
from vnizer.app import SettingsChange
from vnizer.media import speech_chunk
from vnizer.store import Store
from vnizer.tts import pcm_to_wav, speech_request


def external_settings():
    return {"tts_type": "supertonic", "tts_url": "http://tts:5001", "speaker": "F1",
            "language": "English", "tts_api_key": "test-key", "ftt_url": "http://ftt"}


def test_external_speech_becomes_valid_wave(tmp_path):
    def respond(request):
        assert str(request.url) == "http://tts:5001/v1/audio/speech"
        assert request.headers["Authorization"] == "Bearer test-key"
        assert json.loads(request.content) == {"text": "Test.", "voice": "F1", "lang": "en"}
        return httpx.Response(200, content=b"\x01\x00" * 24000,
                              headers={"content-type": "application/octet-stream", "x-sample-rate": "24000"})

    target = tmp_path / "speech.wav"
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        duration = speech_chunk(client, external_settings(), {"text": "Test.", "mood": "serious"}, target)
    assert duration == 1
    with wave.open(str(target)) as audio:
        assert audio.getparams()[:4] == (1, 2, 24000, 24000)


@pytest.mark.parametrize("data,rate", [(b"", "24000"), (b"x", "24000"),
                                         (b"xx", "48000"), (b"xx" * 24000 * 181, "24000")])
def test_invalid_pcm_is_rejected(data, rate):
    with pytest.raises(ValueError):
        pcm_to_wav(data, rate)


@pytest.mark.parametrize("status", [401, 422])
def test_request_failure_does_not_publish_audio(tmp_path, status):
    target = tmp_path / "speech.wav"
    with (httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status))) as client,
          pytest.raises(ValueError, match="TTS request failed")):
        speech_chunk(client, external_settings(), {"text": "Test.", "mood": "neutral"}, target)
    assert not target.exists()


def test_existing_settings_keep_qwen_contract(tmp_path):
    store = Store(tmp_path)
    with store.connect() as db:
        db.execute("UPDATE settings SET value=?", (json.dumps({"tts_url": "http://old", "speaker": "Ryan", "language": "English"}),))
    settings = store.settings()
    assert settings["tts_type"] == "qwen"
    url, body = speech_request(settings, {"text": "Test.", "mood": "serious"})
    assert url == "http://old/speech"
    assert body["speaker"] == "Ryan" and body["mood"] == "serious"
    with pytest.raises(ValueError):
        SettingsChange(tts_type="unknown")


@pytest.mark.parametrize("voice,ready", [("F1", True), ("missing", False)])
def test_service_check_uses_voice_list(monkeypatch, voice, ready):
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "vision"}]})
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(200, json={"choices": [{}]})
        assert request.url.path == "/v1/audio/voices"
        return httpx.Response(200, json={"voices": [{"id": "F1"}]})

    original = httpx.AsyncClient
    monkeypatch.setattr(services.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    settings = external_settings()
    settings["speaker"] = voice
    assert asyncio.run(services.check_services(settings))["ready"] is ready


def test_base_url_accepts_v1_and_language_code():
    settings = external_settings() | {"tts_url": "http://tts/v1/", "language": "id"}
    url, body = speech_request(settings, {"text": "Test."})
    assert url == "http://tts/v1/audio/speech"
    assert body["lang"] == "id"
    with wave.open(io.BytesIO(pcm_to_wav(b"xx", "24000"))) as audio:
        assert audio.getnframes() == 1

import importlib.util
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient


def load_service():
    spec = importlib.util.spec_from_file_location("tts_server", Path("deploy/tts/server.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Model:
    def __init__(self):
        self.calls = []

    def get_supported_speakers(self):
        return ["ryan"]

    def get_supported_languages(self):
        return ["english"]

    def generate_custom_voice(self, **kwargs):
        self.calls.append(kwargs)
        return [np.zeros(2400, dtype=np.float32)], 24000


def test_tts_contract_and_validation(monkeypatch):
    monkeypatch.setenv("TTS_API_KEY", "test-key")
    model = Model()
    with TestClient(load_service().create_app(lambda: model)) as client:
        assert client.get("/health").status_code == 401
        client.headers["Authorization"] = "Bearer test-key"
        assert client.get("/health").json()["status"] == "ready"
        result = client.post("/speech", json={"text": "Test narration.", "mood": "serious"})
        assert result.status_code == 200
        assert result.content.startswith(b"RIFF")
        assert "serious" in model.calls[0]["instruct"]
        assert client.post("/speech", json={"text": "a" * 513}).status_code == 422
        assert client.post("/speech", json={"text": "Test", "language": "unsupported"}).status_code == 422
        assert client.post("/speech", json={"text": "Test", "speaker": "unsupported"}).status_code == 422

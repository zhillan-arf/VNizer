import io
import json
import zipfile

import pymupdf
import pytest
from fastapi.testclient import TestClient

from vnizer.app import create_app
from vnizer.config import Config


@pytest.fixture
def client(tmp_path):
    app = create_app(Config(data_root=tmp_path))

    async def healthy(settings):
        return {"ready": True, "ftt_model": "fixture-vlm", "errors": []}

    app.state.health_check = healthy
    with TestClient(app) as client:
        yield client


def pdf_bytes():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 50), "A test paper.")
        return pdf.tobytes()


def upload(client, count=1):
    return client.post("/api/processes", files=[
        ("files", (f"paper-{i}.pdf", pdf_bytes(), "application/pdf")) for i in range(count)
    ])


def test_multiple_pdfs_snapshot_and_restart(client):
    response = upload(client, 2)
    assert response.status_code == 201
    process = response.json()
    assert len(process["documents"]) == 2
    store = client.app.state.store
    claimed = store.claim()
    original = json.loads(claimed["settings"])
    assert original["ftt_model"] == "fixture-vlm"
    assert client.post("/api/settings", json={"ftt_url": "http://other:1234"}).status_code == 200
    assert json.loads(store.document(claimed["id"])["settings"]) == original
    store.recover()
    assert store.document(claimed["id"])["state"] == "queued"
    assert client.get(f"/api/processes/{process['id']}").status_code == 200


def test_unavailable_services_do_not_create_process(client):
    async def unavailable(settings):
        return {"ready": False, "errors": ["TTS service is unavailable. Return later."]}
    client.app.state.health_check = unavailable
    assert upload(client).status_code == 503
    assert client.get("/api/processes").json() == []


def test_upload_validation_is_atomic(client):
    response = client.post("/api/processes", files=[
        ("files", ("good.pdf", pdf_bytes(), "application/pdf")),
        ("files", ("bad.pdf", b"invalid", "application/pdf")),
    ])
    assert response.status_code == 422
    assert client.get("/api/processes").json() == []
    assert not list((client.app.state.store.root / "processes").glob("*"))


def test_retry_and_cancel(client):
    process = upload(client).json()
    document = process["documents"][0]
    store = client.app.state.store
    store.update_document(document["id"], state="failed", stage="media", error="Test error")
    url = f"/api/documents/{document['id']}/retry"
    assert client.post(url, json={"stage": "transcription"}).status_code == 409
    assert client.post(url, json={"stage": "media"}).status_code == 200
    assert store.document(document["id"])["attempt"] == 2
    assert store.document(document["id"])["stage"] == "media"
    client.post(f"/api/processes/{process['id']}/cancel")
    assert store.document(document["id"])["state"] == "canceled"
    assert store.claim() is None


def test_downloads_and_deletion(client):
    process = upload(client).json()
    doc = process["documents"][0]
    store = client.app.state.store
    path = store.document_root(store.document(doc["id"])) / "transcript.txt"
    path.write_text("Source narration.")
    store.add_artifact(doc["id"], "transcript", path)
    artifact = next(a for a in store.process(process["id"])["documents"][0]["artifacts"]
                    if a["kind"] == "transcript")
    assert client.get(f"/api/artifacts/{artifact['id']}").text == "Source narration."
    data = client.get(f"/api/processes/{process['id']}/download")
    with zipfile.ZipFile(io.BytesIO(data.content)) as archive:
        assert len(archive.namelist()) == 1
        assert archive.read(archive.namelist()[0]) == b"Source narration."
    assert client.delete(f"/api/artifacts/{artifact['id']}").status_code == 409
    store.update_document(doc["id"], state="completed")
    assert client.delete(f"/api/artifacts/{artifact['id']}").status_code == 200
    assert not path.exists()
    assert client.delete(f"/api/processes/{process['id']}").status_code == 200
    assert store.process(process["id"]) is None


def test_auth_and_origin_guard(tmp_path):
    app = create_app(Config(data_root=tmp_path, username="owner", password="secret"))
    with TestClient(app) as client:
        assert client.get("/api/processes").status_code == 401
        assert client.post("/api/login", json={"username": "owner", "password": "bad"}).status_code == 401
        assert client.post("/api/login", json={"username": "owner", "password": "secret"}).status_code == 200
        assert client.get("/api/processes").status_code == 200
        assert client.post("/api/settings", json={}, headers={"Origin": "http://other"}).status_code == 403
        client.post("/api/logout")
        assert client.get("/api/processes").status_code == 401


def test_settings_hide_keys_and_validate_urls(client):
    result = client.post("/api/settings", json={"ftt_api_key": "private"}).json()
    assert "ftt_api_key" not in result
    assert result["ftt_api_key_configured"]
    assert client.post("/api/settings", json={"ftt_url": "file:///etc/passwd"}).status_code == 422
    assert client.post("/api/settings", json={"unknown": "value"}).status_code == 422



def test_health_check_rejects_text_only_ftt(monkeypatch):
    import asyncio

    import httpx

    from vnizer import services
    from vnizer.config import initial_settings

    requests = []

    def handle(request):
        requests.append(request.url.path)
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "fixture"}]})
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ready"})
        return httpx.Response(400, json={"error": "Images are disabled."})

    original = httpx.AsyncClient
    monkeypatch.setattr(services.httpx, "AsyncClient", lambda **kwargs: original(
        transport=httpx.MockTransport(handle), **kwargs))
    result = asyncio.run(services.check_services(initial_settings()))
    assert not result["ready"]
    assert "FTT" in result["errors"][0]
    assert "/v1/chat/completions" in requests

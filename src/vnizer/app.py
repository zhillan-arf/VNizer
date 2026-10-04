import asyncio
import json
import secrets
import shutil
import zipfile
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

import pymupdf
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.sessions import SessionMiddleware

from .config import Config
from .services import check_services
from .store import RUNNING, Store, new_id, now


class Login(BaseModel):
    username: str = ""
    password: str = ""


class SettingsChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ftt_url: str | None = None
    ftt_model: str | None = Field(default=None, max_length=200)
    ftt_api_key: str | None = Field(default=None, max_length=1000)
    tts_url: str | None = None
    tts_api_key: str | None = Field(default=None, max_length=1000)
    speaker: str | None = Field(default=None, min_length=1, max_length=80)
    language: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("ftt_url", "tts_url")
    @classmethod
    def valid_url(cls, value):
        if value is None:
            return value
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("Use an HTTP or HTTPS service URL.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Do not include credentials, queries, or fragments in a service URL.")
        return value.rstrip("/")


class Retry(BaseModel):
    stage: str


def public_settings(settings):
    result = {k: v for k, v in settings.items() if not k.endswith("api_key")}
    for key in ("ftt_api_key", "tts_api_key"):
        result[key + "_configured"] = bool(settings.get(key))
    return result


def create_app(config=None):
    config = config or Config.from_env()
    store = Store(config.data_root)
    app = FastAPI(title="VNizer")
    app.state.store = store
    app.state.config = config
    app.state.health_check = check_services
    app.add_middleware(SessionMiddleware, secret_key=config.secret, same_site="strict",
                       https_only=config.secure_cookie, max_age=86400)

    @app.middleware("http")
    async def origin_guard(request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return HTMLResponse("Cross-origin requests are not permitted.", status_code=403)
            if request.headers.get("sec-fetch-site") == "cross-site":
                return HTMLResponse("Cross-site requests are not permitted.", status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        return response

    def require_session(request: Request):
        if config.username and not request.session.get("authenticated"):
            raise HTTPException(401, "Sign in to continue.")

    secure = [Depends(require_session)]

    def get_process(process_id):
        process = store.process(process_id)
        if not process:
            raise HTTPException(404, "Process not found.")
        return process

    @app.get("/api/session")
    def session(request: Request):
        return {"auth_required": bool(config.username),
                "authenticated": not config.username or bool(request.session.get("authenticated"))}

    @app.post("/api/login")
    def login(body: Login, request: Request):
        if config.username and not (
            secrets.compare_digest(body.username.encode(), config.username.encode())
            and secrets.compare_digest(body.password.encode(), config.password.encode())
        ):
            raise HTTPException(401, "The username or password is incorrect.")
        request.session.clear()
        request.session["authenticated"] = True
        return {"ok": True}

    @app.post("/api/logout")
    def logout(request: Request):
        request.session.clear()
        return {"ok": True}

    @app.get("/api/settings", dependencies=secure)
    def settings():
        return public_settings(store.settings())

    @app.post("/api/settings", dependencies=secure)
    def save_settings(body: SettingsChange):
        return public_settings(store.save_settings(body.model_dump(exclude_none=True)))

    @app.post("/api/health-check", dependencies=secure)
    async def health_check():
        return await app.state.health_check(store.settings())

    @app.get("/api/processes", dependencies=secure)
    def processes():
        return store.processes()

    @app.get("/api/processes/{process_id}", dependencies=secure)
    def process(process_id: str):
        return get_process(process_id)

    @app.post("/api/processes", dependencies=secure, status_code=201)
    async def create_process(files: Annotated[list[UploadFile], File()]):
        if not 1 <= len(files) <= config.max_files:
            raise HTTPException(422, f"Select between 1 and {config.max_files} PDF files.")
        snapshot = store.settings()
        health = await app.state.health_check(snapshot)
        if not health["ready"]:
            raise HTTPException(503, " ".join(health["errors"]))
        snapshot["ftt_model"] = health["ftt_model"]
        process_id = new_id()
        root = store.root / "processes" / process_id
        documents = []
        try:
            for upload in files:
                name = (upload.filename or "document.pdf").replace("\\", "/").rsplit("/", 1)[-1]
                if not name.lower().endswith(".pdf") or len(name) > 250:
                    raise HTTPException(422, "Each file must have a PDF filename of at most 250 characters.")
                document_id = new_id()
                path = root / document_id / "source.pdf"
                path.parent.mkdir(parents=True)
                size = 0
                with path.open("wb") as output:
                    while block := await upload.read(1024 * 1024):
                        size += len(block)
                        if size > config.max_file_bytes:
                            raise HTTPException(413, "A PDF exceeds the upload size limit.")
                        output.write(block)
                try:
                    with pymupdf.open(path) as pdf:
                        if not pdf.is_pdf or pdf.needs_pass or not 1 <= len(pdf) <= config.max_pages:
                            raise ValueError("Unsupported PDF.")
                        pages = len(pdf)
                except Exception as exc:
                    raise HTTPException(422, "A PDF is invalid, encrypted, empty, or too long.") from exc
                documents.append({"id": document_id, "name": name, "pages": pages, "path": path})
            store.create_process(process_id, documents, snapshot)
        except BaseException:
            shutil.rmtree(root, ignore_errors=True)
            raise
        finally:
            for upload in files:
                await upload.close()
        return get_process(process_id)

    @app.post("/api/processes/{process_id}/cancel", dependencies=secure)
    def cancel(process_id: str):
        get_process(process_id)
        store.cancel(process_id)
        return {"ok": True, "message": "Stop requested. The worker will stop the active document."}

    @app.post("/api/documents/{document_id}/retry", dependencies=secure)
    async def retry(document_id: str, body: Retry):
        document = store.document(document_id)
        if not document:
            raise HTTPException(404, "Document not found.")
        if document["state"] not in ("failed", "canceled") or body.stage != document["stage"]:
            raise HTTPException(409, "Retry the failed or canceled stage shown for this document.")
        snapshot = store.settings()
        health = await app.state.health_check(snapshot)
        if not health["ready"]:
            raise HTTPException(503, " ".join(health["errors"]))
        snapshot["ftt_model"] = health["ftt_model"]
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute("""UPDATE documents SET state='queued',error=NULL,settings=?,
                attempt=attempt+1,updated=? WHERE id=? AND state IN ('failed','canceled')""",
                                (json.dumps(snapshot), now(), document_id))
            if cursor.rowcount != 1:
                raise HTTPException(409, "The document state changed. Reload this page.")
            db.execute("UPDATE processes SET canceled=0 WHERE id=?", (document["process_id"],))
        return {"ok": True}

    @app.delete("/api/processes/{process_id}", dependencies=secure)
    async def delete_process(process_id: str):
        get_process(process_id)
        store.cancel(process_id)
        for _ in range(50):
            current = get_process(process_id)
            if not any(d["state"] in RUNNING for d in current["documents"]):
                break
            await asyncio.sleep(0.1)
        else:
            raise HTTPException(409, "Stop is pending. Retry deletion after the worker stops.")
        with store.connect() as db:
            db.execute("DELETE FROM processes WHERE id=?", (process_id,))
        shutil.rmtree(store.root / "processes" / process_id, ignore_errors=True)
        return {"ok": True}

    @app.get("/api/artifacts/{artifact_id}", dependencies=secure)
    def artifact(artifact_id: str):
        item = store.artifact(artifact_id)
        if not item or not store.file_path(item["path"]).is_file():
            raise HTTPException(404, "Artifact not found.")
        doc = store.document(item["document_id"])
        suffix = Path(item["path"]).suffix
        filename = f"{Path(doc['name']).stem}-{item['kind']}{suffix}"
        return FileResponse(store.file_path(item["path"]), filename=filename)

    @app.delete("/api/artifacts/{artifact_id}", dependencies=secure)
    def delete_artifact(artifact_id: str):
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            item = db.execute("""SELECT a.*,d.state FROM artifacts a JOIN documents d
                ON d.id=a.document_id WHERE a.id=?""", (artifact_id,)).fetchone()
            if not item:
                raise HTTPException(404, "Artifact not found.")
            if item["state"] in (*RUNNING, "queued"):
                raise HTTPException(409, "Stop the document before deleting its artifacts.")
            store.file_path(item["path"]).unlink(missing_ok=True)
            db.execute("DELETE FROM artifacts WHERE id=?", (artifact_id,))
        return {"ok": True}

    @app.get("/api/processes/{process_id}/download", dependencies=secure)
    def download_all(process_id: str):
        process = get_process(process_id)
        # A temporary file prevents large archives from exhausting memory.
        import tempfile
        output = tempfile.TemporaryFile()  # noqa: SIM115 - Closed by the response iterator.
        count = 0
        with zipfile.ZipFile(output, "w", zipfile.ZIP_STORED) as archive:
            for index, doc in enumerate(process["documents"], 1):
                for artifact in doc["artifacts"]:
                    if artifact["kind"] not in ("transcript", "audio", "video"):
                        continue
                    item = store.artifact(artifact["id"])
                    path = store.file_path(item["path"])
                    if path.is_file():
                        archive.write(path, f"{index:03}-{Path(doc['name']).stem}/{path.name}")
                        count += 1
        if not count:
            output.close()
            raise HTTPException(409, "No completed outputs are available.")
        output.seek(0)

        def stream():
            try:
                while block := output.read(1024 * 1024):
                    yield block
            finally:
                output.close()

        return StreamingResponse(stream(), media_type="application/zip", headers={
            "Content-Disposition": f'attachment; filename="vnizer-{process_id}.zip"'})

    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/", response_class=HTMLResponse)
    @app.get("/upload", response_class=HTMLResponse)
    @app.get("/admin", response_class=HTMLResponse)
    @app.get("/{process_id}", response_class=HTMLResponse)
    def page():
        index = static / "index.html"
        if index.exists():
            return index.read_text()
        return "<h1>VNizer</h1><p>The web interface is under construction.</p>"

    return app

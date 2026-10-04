import asyncio
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .avatars import add_avatar, seed_avatars
from .store import MOODS


def router(store, dependencies):
    routes = APIRouter(prefix="/api/avatars", dependencies=dependencies)
    seed_avatars(store)

    @routes.get("")
    def listing():
        with store.connect() as db:
            rows = db.execute("SELECT * FROM avatars ORDER BY mood,selected DESC,name").fetchall()
            return [{"id": row["id"], "name": row["name"], "mood": row["mood"],
                     "selected": row["selected"], "builtin": row["builtin"],
                     "media_type": "video" if Path(row["path"]).suffix in (".mp4", ".webm") else "image"}
                    for row in rows]

    @routes.get("/{avatar_id}/preview")
    def preview(avatar_id: str):
        with store.connect() as db:
            row = db.execute("SELECT path FROM avatars WHERE id=?", (avatar_id,)).fetchone()
        if not row or not store.file_path(row["path"]).is_file():
            raise HTTPException(404, "Avatar not found.")
        return FileResponse(store.file_path(row["path"]))

    @routes.post("", status_code=201)
    async def upload(file: Annotated[UploadFile, File()], mood: Annotated[str, Form()],
                     name: Annotated[str, Form()] = "Custom avatar"):
        if mood not in MOODS or not 1 <= len(name.strip()) <= 120:
            raise HTTPException(422, "Select a mood and enter a name of at most 120 characters.")
        suffix = Path(file.filename or "").suffix.lower()
        try:
            with tempfile.TemporaryDirectory(prefix="vnizer-avatar-") as directory:
                path = Path(directory) / ("upload" + suffix)
                count = 0
                with path.open("wb") as output:
                    while block := await file.read(1024 * 1024):
                        count += len(block)
                        if count > 50 * 1024 * 1024:
                            raise HTTPException(413, "Avatar files must not exceed 50 MiB.")
                        output.write(block)
                try:
                    avatar_id = await asyncio.to_thread(add_avatar, store, path, name.strip(), mood)
                except Exception as exc:
                    raise HTTPException(422, "The avatar cannot be decoded or exceeds the media limits.") from exc
        finally:
            await file.close()
        return {"id": avatar_id}

    @routes.post("/{avatar_id}/select")
    def select(avatar_id: str):
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT mood FROM avatars WHERE id=?", (avatar_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Avatar not found.")
            db.execute("UPDATE avatars SET selected=0 WHERE mood=?", (row["mood"],))
            db.execute("UPDATE avatars SET selected=1 WHERE id=?", (avatar_id,))
        return {"ok": True}

    @routes.delete("/{avatar_id}")
    def delete(avatar_id: str):
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM avatars WHERE id=?", (avatar_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Avatar not found.")
            other = db.execute("SELECT id FROM avatars WHERE mood=? AND id!=? ORDER BY builtin DESC LIMIT 1",
                               (row["mood"], avatar_id)).fetchone()
            if not other:
                raise HTTPException(409, "Add another avatar for this mood before deleting the last one.")
            db.execute("DELETE FROM avatars WHERE id=?", (avatar_id,))
            if row["selected"]:
                db.execute("UPDATE avatars SET selected=1 WHERE id=?", (other["id"],))
            store.file_path(row["path"]).unlink(missing_ok=True)
        return {"ok": True}

    return routes

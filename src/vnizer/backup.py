"""Create and restore verified offline backups without replacing existing data."""

import fcntl
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from .files import atomic_json, digest_file
from .store import Store


def backup(root, destination):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if destination.exists() or destination.is_relative_to(root):
        raise ValueError("Use a new backup directory outside the data directory.")
    if not (root / "vnizer.sqlite3").is_file():
        raise ValueError("The source data directory has no database.")
    store = Store(root)
    with (root / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Stop the worker before creating a backup.") from exc
        destination.mkdir(parents=True, mode=0o700)
        try:
            with (closing(sqlite3.connect(store.path)) as source,
                  closing(sqlite3.connect(destination / "vnizer.sqlite3")) as target):
                source.backup(target)
            for path in root.iterdir():
                if path.name.startswith("vnizer.sqlite3") or path.name.endswith(".lock"):
                    continue
                if path.is_symlink() or (path.is_dir() and any(p.is_symlink() for p in path.rglob("*"))):
                    raise ValueError("Backup does not permit symbolic links in the data directory.")
                if path.is_dir():
                    shutil.copytree(path, destination / path.name)
                else:
                    shutil.copy2(path, destination / path.name)
            with closing(sqlite3.connect(destination / "vnizer.sqlite3")) as db:
                db.row_factory = sqlite3.Row
                exported = {table: [dict(row) for row in db.execute(f"SELECT * FROM {table}")]
                            for table in ("settings", "processes", "documents", "artifacts", "avatars")}
            atomic_json(destination / "records.json", {"schema_version": 1, "tables": exported})
            files = [{"path": str(path.relative_to(destination)), "bytes": path.stat().st_size,
                      "sha256": digest_file(path)} for path in sorted(destination.rglob("*")) if path.is_file()]
            atomic_json(destination / "backup.json", {"schema_version": 1, "files": files})
        except BaseException:
            shutil.rmtree(destination)
            raise
    return destination


def restore(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists() or destination.is_relative_to(source):
        raise ValueError("Restore requires a new directory outside the backup directory.")
    manifest = json.loads((source / "backup.json").read_text())
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported backup schema.")
    verified = []
    for item in manifest["files"]:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("The backup contains an invalid file path.")
        path = (source / relative).resolve()
        if not path.is_relative_to(source) or not path.is_file() or path.is_symlink():
            raise ValueError("The backup contains an invalid file path.")
        if path.stat().st_size != item["bytes"] or digest_file(path) != item["sha256"]:
            raise ValueError(f"Backup checksum mismatch: {item['path']}")
        verified.append((path, item["path"]))
    destination.mkdir(parents=True, mode=0o700)
    try:
        for path, relative in verified:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        with closing(sqlite3.connect(destination / "vnizer.sqlite3")) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("The restored database failed its integrity check.")
            if db.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("The restored database has invalid record references.")
    except BaseException:
        shutil.rmtree(destination)
        raise
    return destination

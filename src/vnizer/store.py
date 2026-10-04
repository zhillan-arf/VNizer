import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .config import initial_settings

RUNNING = ("parsing", "rendering")
TERMINAL = ("completed", "failed", "canceled")
MOODS = ("neutral", "explaining", "curious", "positive", "serious")


def now():
    return datetime.now(UTC).isoformat()


def new_id():
    return uuid.uuid4().hex


class Store:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "vnizer.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS processes (
                    id TEXT PRIMARY KEY, created TEXT NOT NULL, settings TEXT NOT NULL,
                    canceled INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, process_id TEXT NOT NULL REFERENCES processes(id)
                        ON DELETE CASCADE,
                    name TEXT NOT NULL, pages INTEGER NOT NULL, state TEXT NOT NULL,
                    stage TEXT NOT NULL DEFAULT 'transcription', progress INTEGER NOT NULL DEFAULT 0,
                    total INTEGER NOT NULL DEFAULT 0, error TEXT,
                    attempt INTEGER NOT NULL DEFAULT 1, settings TEXT NOT NULL,
                    updated TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id)
                        ON DELETE CASCADE,
                    kind TEXT NOT NULL, path TEXT NOT NULL UNIQUE, size INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS avatars (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, mood TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE, selected INTEGER NOT NULL DEFAULT 0,
                    builtin INTEGER NOT NULL DEFAULT 0
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_selected_avatar ON avatars(mood)
                    WHERE selected=1;
                PRAGMA user_version=1;
            """)
            db.execute("INSERT OR IGNORE INTO settings VALUES (1, ?)",
                       (json.dumps(initial_settings()),))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def settings(self):
        with self.connect() as db:
            return json.loads(db.execute("SELECT value FROM settings WHERE id=1").fetchone()[0])

    def save_settings(self, changes):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = json.loads(db.execute("SELECT value FROM settings WHERE id=1").fetchone()[0])
            current.update(changes)
            db.execute("UPDATE settings SET value=? WHERE id=1", (json.dumps(current),))
        return current

    def create_process(self, process_id, documents, settings):
        snapshot = json.dumps(settings)
        with self.connect() as db:
            db.execute("INSERT INTO processes (id,created,settings) VALUES (?,?,?)",
                       (process_id, now(), snapshot))
            for document in documents:
                db.execute("""INSERT INTO documents
                    (id,process_id,name,pages,state,settings,updated) VALUES (?,?,?,?,?,?,?)""",
                           (document["id"], process_id, document["name"], document["pages"],
                            "queued", snapshot, now()))
                self._artifact(db, document["id"], "source", document["path"])

    def _artifact(self, db, document_id, kind, path):
        relative = str(Path(path).relative_to(self.root))
        db.execute("""INSERT INTO artifacts VALUES (?,?,?,?,?)
            ON CONFLICT(path) DO UPDATE SET size=excluded.size, kind=excluded.kind""",
                   (new_id(), document_id, kind, relative, Path(path).stat().st_size))

    def add_artifact(self, document_id, kind, path):
        with self.connect() as db:
            self._artifact(db, document_id, kind, path)

    def document(self, document_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        return dict(row) if row else None

    def process(self, process_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM processes WHERE id=?", (process_id,)).fetchone()
            if not row:
                return None
            result = dict(row)
            result.pop("settings")
            result["documents"] = []
            for row in db.execute("SELECT * FROM documents WHERE process_id=? ORDER BY rowid",
                                  (process_id,)):
                doc = dict(row)
                doc.pop("settings")
                doc["artifacts"] = [dict(a) for a in db.execute(
                    "SELECT id,kind,size,path FROM artifacts WHERE document_id=?", (doc["id"],))]
                for artifact in doc["artifacts"]:
                    artifact["name"] = str(Path(artifact.pop("path")).relative_to(
                        Path("processes") / process_id / doc["id"]))
                result["documents"].append(doc)
            states = [d["state"] for d in result["documents"]]
            result["state"] = (
                "completed" if states and all(s == "completed" for s in states)
                else "running" if any(s in RUNNING for s in states)
                else "queued" if "queued" in states
                else "failed" if "failed" in states else "canceled"
            )
            return result

    def processes(self):
        with self.connect() as db:
            ids = [r[0] for r in db.execute("SELECT id FROM processes ORDER BY created DESC")]
        return [self.process(i) for i in ids]

    def sync_work_artifacts(self):
        with self.connect() as db:
            documents = [dict(row) for row in db.execute("SELECT * FROM documents")]
            for document in documents:
                root = self.document_root(document)
                for path in root.rglob("*"):
                    if not path.is_file() or path.is_symlink():
                        continue
                    try:
                        size = path.stat().st_size
                    except FileNotFoundError:
                        continue
                    relative = str(path.relative_to(self.root))
                    db.execute("""INSERT INTO artifacts VALUES (?,?,?,?,?)
                        ON CONFLICT(path) DO UPDATE SET size=excluded.size""",
                               (new_id(), document["id"], "work", relative, size))
            for row in db.execute("SELECT id,path FROM artifacts").fetchall():
                if not self.file_path(row["path"]).is_file():
                    db.execute("DELETE FROM artifacts WHERE id=?", (row["id"],))

    def artifact(self, artifact_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM artifacts WHERE id=?", (artifact_id,)).fetchone()
        return dict(row) if row else None

    def file_path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Artifact path is outside the data directory.")
        return path

    def document_root(self, document):
        return self.root / "processes" / document["process_id"] / document["id"]

    def update_document(self, document_id, **values):
        allowed = {"state", "stage", "progress", "total", "error", "settings", "attempt"}
        if not values or not values.keys() <= allowed:
            raise ValueError("Invalid document update.")
        values["updated"] = now()
        with self.connect() as db:
            db.execute(f"UPDATE documents SET {','.join(k+'=?' for k in values)} WHERE id=?",
                       (*values.values(), document_id))

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""SELECT d.* FROM documents d JOIN processes p ON p.id=d.process_id
                WHERE d.state='queued' AND p.canceled=0 ORDER BY p.created, d.rowid LIMIT 1""").fetchone()
            if row:
                state = "parsing" if row["stage"] == "transcription" else "rendering"
                db.execute("UPDATE documents SET state=?,updated=? WHERE id=?",
                           (state, now(), row["id"]))
                return self.document_after_claim(row, state)
        return None

    @staticmethod
    def document_after_claim(row, state):
        result = dict(row)
        result["state"] = state
        return result

    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE documents SET state='queued' WHERE state IN ('parsing','rendering')")
            db.execute("""UPDATE documents SET state='canceled' WHERE process_id IN
                (SELECT id FROM processes WHERE canceled=1) AND state='queued'""")

    def cancel(self, process_id):
        with self.connect() as db:
            db.execute("UPDATE processes SET canceled=1 WHERE id=?", (process_id,))
            db.execute("""UPDATE documents SET state='canceled',updated=? WHERE process_id=?
                AND state='queued'""", (now(), process_id))

    def is_canceled(self, document_id):
        with self.connect() as db:
            row = db.execute("""SELECT p.canceled FROM processes p JOIN documents d
                ON d.process_id=p.id WHERE d.id=?""", (document_id,)).fetchone()
        return row is None or bool(row[0])

"""Run one durable queue worker per data directory."""

import fcntl
import os
import signal
import subprocess
import sys
import time

from .avatars import snapshot_avatars
from .config import Config
from .store import Store


def stop_child(child):
    if child.poll() is None:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()


def run_document(store, document, stopping, command=None):
    snapshot_avatars(store, document)
    command = command or [sys.executable, "-m", "vnizer.pipeline", document["id"]]
    log = store.document_root(document) / "worker.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, VNIZER_DATA_ROOT=str(store.root))
    with log.open("ab") as output:
        child = subprocess.Popen(command, stdout=output, stderr=output,
                                 start_new_session=True, env=environment)
        try:
            while child.poll() is None:
                if stopping() or store.is_canceled(document["id"]):
                    stop_child(child)
                    state = "canceled" if store.is_canceled(document["id"]) else "queued"
                    store.update_document(document["id"], state=state)
                    return
                time.sleep(0.1)
            current = store.document(document["id"])
            if store.is_canceled(document["id"]):
                store.update_document(document["id"], state="canceled")
            elif current and current["state"] not in ("completed", "failed"):
                store.update_document(document["id"], state="failed",
                                      error="The worker task stopped. Inspect worker.log and retry.")
        finally:
            stop_child(child)


def main():
    config = Config.from_env()
    store = Store(config.data_root)
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with (store.root / "worker.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SystemExit("A worker already uses this data directory.") from exc
        store.recover()
        while not stopped:
            document = store.claim()
            if document:
                run_document(store, document, lambda: stopped)
            else:
                time.sleep(0.5)


if __name__ == "__main__":
    main()

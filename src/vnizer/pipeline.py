import sys
import traceback

from .config import Config
from .store import Store
from .transcribe import transcribe


def run(store, document_id):
    document = store.document(document_id)
    if not document:
        return
    try:
        if store.is_canceled(document_id):
            raise InterruptedError("Process canceled.")
        if document["stage"] == "transcription":
            transcribe(store, document)
        from .media import render_document
        render_document(store, store.document(document_id))
        if store.is_canceled(document_id):
            raise InterruptedError("Process canceled.")
        store.update_document(document_id, state="completed", error=None)
    except InterruptedError:
        store.update_document(document_id, state="canceled")
    except Exception as exc:  # noqa: BLE001 - Persist failures at the task boundary.
        traceback.print_exc()
        store.update_document(document_id, state="failed", error=str(exc)[:1500])


if __name__ == "__main__":
    run(Store(Config.from_env().data_root), sys.argv[1])

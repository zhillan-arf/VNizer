import sys
import threading
import time

from vnizer.store import Store, new_id
from vnizer.worker import run_document


def test_worker_stops_active_child(tmp_path):
    store = Store(tmp_path)
    process_id, document_id = new_id(), new_id()
    path = tmp_path / "processes" / process_id / document_id / "source.pdf"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"fixture")
    store.create_process(process_id, [{"id": document_id, "name": "source.pdf",
                                      "pages": 1, "path": path}], store.settings())
    document = store.claim()
    thread = threading.Thread(target=run_document, args=(store, document, lambda: False),
                              kwargs={"command": [sys.executable, "-c", "import time; time.sleep(60)"]})
    thread.start()
    time.sleep(0.2)
    store.cancel(process_id)
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert store.document(document_id)["state"] == "canceled"

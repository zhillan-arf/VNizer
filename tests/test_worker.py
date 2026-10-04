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


def test_child_exits_when_parent_is_killed(tmp_path):
    import os
    import signal
    import subprocess

    marker = tmp_path / 'child.pid'
    script = tmp_path / 'parent.py'
    script.write_text('''import os,subprocess,sys,time
subprocess.Popen([sys.executable,'-m','vnizer.child',str(os.getpid()),sys.executable,'-c',
                  "import os,time;from pathlib import Path;Path("+repr(sys.argv[1])+").write_text(str(os.getpid()));time.sleep(60)"])
time.sleep(60)
''')
    parent = subprocess.Popen([sys.executable, str(script), str(marker)])
    try:
        for _ in range(100):
            if marker.exists():
                break
            time.sleep(0.05)
        assert marker.exists()
        child_pid = int(marker.read_text())
        parent.kill()
        parent.wait(timeout=5)
        for _ in range(100):
            stat = tmp_path.__class__(f'/proc/{child_pid}/stat')
            if not stat.exists() or stat.read_text().split()[2] == 'Z':
                break
            time.sleep(0.05)
        else:
            os.kill(child_pid, signal.SIGKILL)
            raise AssertionError('The child survived its parent.')
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=5)


def test_shutdown_preserves_a_terminal_document_state(tmp_path):
    store = Store(tmp_path)
    process_id, document_id = new_id(), new_id()
    path = tmp_path / 'processes' / process_id / document_id / 'source.pdf'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'fixture')
    store.create_process(process_id, [{'id': document_id, 'name': 'source.pdf', 'pages': 1,
                                      'path': path}], store.settings())
    marker = tmp_path / 'failed'
    command = [sys.executable, '-c',
               ('import time,sys;from pathlib import Path;from vnizer.store import Store;'
               'Store(Path(sys.argv[1])).update_document(sys.argv[2],state="failed",error="Fixture failure");'
               'Path(sys.argv[3]).touch();time.sleep(60)'), str(tmp_path), document_id, str(marker)]
    run_document(store, store.claim(), marker.exists, command)
    assert store.document(document_id)['state'] == 'failed'

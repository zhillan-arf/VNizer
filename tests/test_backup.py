import fcntl

import pytest

from vnizer.avatars import seed_avatars
from vnizer.backup import backup, restore
from vnizer.store import Store


def test_backup_restore_and_checksum(tmp_path):
    store = Store(tmp_path / 'data')
    seed_avatars(store)
    store.save_settings({'speaker': 'Ryan'})
    saved = backup(store.root, tmp_path / 'backup')
    restored = restore(saved, tmp_path / 'restored')
    assert Store(restored).settings() == store.settings()
    with Store(restored).connect() as db:
        assert db.execute('SELECT COUNT(*) FROM avatars').fetchone()[0] == 5
    assert (restored / 'avatars/builtin-neutral.png').read_bytes() == (store.root / 'avatars/builtin-neutral.png').read_bytes()
    with pytest.raises(ValueError, match='new directory'):
        restore(saved, restored)
    (saved / 'avatars/builtin-neutral.png').write_bytes(b'corrupted')
    with pytest.raises(ValueError, match='checksum'):
        restore(saved, tmp_path / 'broken')
    assert not (tmp_path / 'broken').exists()


def test_backup_refuses_running_worker(tmp_path):
    store = Store(tmp_path / 'data')
    with (store.root / 'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ValueError, match='Stop the worker'):
            backup(store.root, tmp_path / 'backup')


def test_backup_remains_valid_after_creator_exits(tmp_path):
    import subprocess
    import sys

    store = Store(tmp_path / 'source')
    seed_avatars(store)
    target = tmp_path / 'backup'
    subprocess.run([sys.executable, '-c',
                    'import sys;from vnizer.backup import backup;backup(sys.argv[1],sys.argv[2])',
                    str(store.root), str(target)], check=True)
    restored = restore(target, tmp_path / 'restored')
    assert (restored / 'vnizer.sqlite3').exists()

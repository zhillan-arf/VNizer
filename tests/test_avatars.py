import io

from fastapi.testclient import TestClient
from PIL import Image

from vnizer.app import create_app
from vnizer.avatars import seed_avatars
from vnizer.config import Config


def test_avatar_upload_selection_deletion_and_preview(tmp_path):
    app = create_app(Config(data_root=tmp_path))
    with TestClient(app) as client:
        initial = client.get('/api/avatars').json()
        assert len(initial) == 5
        assert client.delete('/api/avatars/builtin-neutral').status_code == 409
        image = io.BytesIO()
        Image.new('RGBA', (40, 40), 'teal').save(image, format='PNG')
        result = client.post('/api/avatars', data={'name': 'New guide', 'mood': 'neutral'},
                             files={'file': ('guide.png', image.getvalue(), 'image/png')})
        assert result.status_code == 201
        avatar_id = result.json()['id']
        assert client.get(f'/api/avatars/{avatar_id}/preview').content == image.getvalue()
        assert client.post(f'/api/avatars/{avatar_id}/select').status_code == 200
        rows = client.get('/api/avatars').json()
        assert next(a for a in rows if a['id'] == avatar_id)['selected']
        assert client.delete('/api/avatars/builtin-neutral').status_code == 200
        seed_avatars(app.state.store)
        assert not any(a['id'] == 'builtin-neutral' for a in client.get('/api/avatars').json())
        assert client.post('/api/avatars', data={'name': 'Bad', 'mood': 'neutral'},
                           files={'file': ('bad.mp4', b'bad', 'video/mp4')}).status_code == 422


def test_attempt_keeps_its_selected_avatar_after_admin_change(tmp_path):
    from vnizer.avatars import add_avatar, snapshot_avatars
    from vnizer.files import digest_file
    from vnizer.store import Store, new_id

    store = Store(tmp_path)
    seed_avatars(store)
    document = {'id': new_id(), 'process_id': new_id(), 'attempt': 1}
    snapshot = snapshot_avatars(store, document)
    initial = digest_file(store.file_path(snapshot['neutral']))
    new_file = tmp_path / 'new.png'
    Image.new('RGB', (40, 40), 'orange').save(new_file)
    avatar_id = add_avatar(store, new_file, 'New guide', 'neutral')
    with store.connect() as db:
        db.execute("UPDATE avatars SET selected=0 WHERE mood='neutral'")
        db.execute('UPDATE avatars SET selected=1 WHERE id=?', (avatar_id,))
    assert snapshot_avatars(store, document) == snapshot
    assert digest_file(store.file_path(snapshot['neutral'])) == initial
    document['attempt'] = 2
    replacement = snapshot_avatars(store, document)
    assert digest_file(store.file_path(replacement['neutral'])) != initial

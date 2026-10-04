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

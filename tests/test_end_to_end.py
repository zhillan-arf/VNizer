"""Run the actual worker and FFmpeg against local HTTP service fixtures."""

import io
import json
import os
import subprocess
import sys
import threading
import time
import wave
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pymupdf
from fastapi.testclient import TestClient

from vnizer.app import create_app
from vnizer.config import Config


def test_complete_worker_pipeline_and_media_retry(tmp_path):
    calls = {'pages': 0, 'speech': 0}
    state = {'fail_speech': True}
    audio = io.BytesIO()
    with wave.open(audio, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b'\0\0' * 12000)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, value, status=200):
            content = value if isinstance(value, bytes) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'audio/wav' if isinstance(value, bytes) else 'application/json')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            if self.path == '/v1/models':
                self.send({'data': [{'id': 'fixture-vlm'}]})
            else:
                self.send({'status': 'ready', 'speakers': ['Ryan'], 'languages': ['English']})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if self.path == '/speech':
                calls['speech'] += 1
                if state['fail_speech']:
                    self.send({'error': 'Fixture failure'}, 400)
                else:
                    self.send(audio.getvalue())
                return
            probe = body['messages'][-1]['content'][0]['text'] == 'Reply OK.'
            if not probe:
                calls['pages'] += 1
            content = 'OK' if probe else json.dumps({'blank': False, 'warnings': [], 'blocks': [
                {'role': 'paragraph', 'text': 'The result is uncertain. More measurements are necessary.', 'mood': 'serious'},
                {'role': 'table', 'text': 'Table one. Group A: twelve meters. Group B: fifteen meters.', 'mood': 'explaining'},
            ]})
            self.send({'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]})

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f'http://127.0.0.1:{server.server_port}'
    root = tmp_path / 'data'
    app = create_app(Config(data_root=root))
    env = dict(os.environ, VNIZER_DATA_ROOT=str(root))
    env.pop('PYTHONPATH', None)
    worker = None
    try:
        with TestClient(app) as client:
            client.post('/api/settings', json={'ftt_url': endpoint, 'tts_url': endpoint})
            with pymupdf.open() as pdf:
                pdf.new_page().insert_text((50, 50), 'Group A: 12 meters. Group B: 15 meters.')
                data = pdf.tobytes()
            result = client.post('/api/processes', files=[('files', (name, data, 'application/pdf'))
                                                         for name in ('First.pdf', 'Second.pdf')])
            assert result.status_code == 201
            process_id = result.json()['id']
            worker = subprocess.Popen([sys.executable, '-m', 'vnizer.worker'], env=env)

            def wait_for(target):
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    process = client.get(f'/api/processes/{process_id}').json()
                    if all(d['state'] == target for d in process['documents']):
                        return process
                    assert worker.poll() is None, 'The worker stopped unexpectedly.'
                    time.sleep(0.1)
                raise AssertionError(process)

            failed = wait_for('failed')
            assert all(d['stage'] == 'media' for d in failed['documents'])
            assert calls['pages'] == 2
            state['fail_speech'] = False
            worker.terminate()
            worker.wait(timeout=10)
            for document in failed['documents']:
                assert client.post(f"/api/documents/{document['id']}/retry", json={'stage': 'media'}).status_code == 200
            worker = subprocess.Popen([sys.executable, '-m', 'vnizer.worker'], env=env)
            completed = wait_for('completed')
            assert calls['pages'] == 2
            for document in completed['documents']:
                outputs = [a for a in document['artifacts'] if a['kind'] in ('transcript', 'audio', 'video')]
                assert len(outputs) == 3
                for artifact in outputs:
                    response = client.get(f"/api/artifacts/{artifact['id']}")
                    assert response.status_code == 200
                    assert response.content
                record = app.state.store.document(document['id'])
                video = app.state.store.document_root(record) / 'video.mp4'
                probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(video)]))
                assert {s['codec_type'] for s in probe['streams']} == {'audio', 'video'}
            archive = client.get(f'/api/processes/{process_id}/download')
            with zipfile.ZipFile(io.BytesIO(archive.content)) as bundle:
                assert len(bundle.namelist()) == 6
    finally:
        if worker and worker.poll() is None:
            worker.terminate()
            worker.wait(timeout=10)
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

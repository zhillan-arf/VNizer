"""Browser workflow checks against the real application API."""

import socket
import threading
import time
from pathlib import Path

import pymupdf
import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright

from vnizer.app import create_app
from vnizer.config import Config


@pytest.fixture
def web(tmp_path):
    app = create_app(Config(data_root=tmp_path / 'data'))

    async def healthy(settings):
        return {'ready': True, 'ftt_model': 'fixture', 'errors': []}

    app.state.health_check = healthy
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        yield page, app, f'http://127.0.0.1:{port}', tmp_path
        browser.close()
    server.should_exit = True
    thread.join(timeout=5)
    listener.close()


def pdf_file(path):
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((50, 50), 'Research note.')
        pdf.save(path)
    return path


def test_upload_progress_retry_download_and_admin(web):
    page, app, url, root = web
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    evidence = Path('/tmp/vnizer/p06')
    evidence.mkdir(parents=True, exist_ok=True)
    page.goto(url)
    expect(page.get_by_role('button', name='Enter the studio')).to_be_visible()
    page.screenshot(path=str(evidence / 'auth-desktop.png'), full_page=True)
    page.get_by_role('button', name='Enter the studio').click()
    expect(page).to_have_url(url + '/upload')
    expect(page.get_by_role('heading', name='Add your documents')).to_be_visible()
    page.screenshot(path=str(evidence / 'upload-desktop.png'), full_page=True)
    page.locator('#pdf-files').set_input_files([pdf_file(root / 'Methods.pdf'), pdf_file(root / 'Results.pdf')])
    page.get_by_role('button', name='Convert documents').click()
    expect(page.locator('.document')).to_have_count(2)
    process_id = page.url.rsplit('/', 1)[1]
    store = app.state.store
    document = store.process(process_id)['documents'][0]
    store.update_document(document['id'], state='failed', error='The service stopped. Retry transcription.')
    page.reload()
    retry = page.get_by_role('button', name='Retry transcription')
    expect(retry).to_be_visible()
    retry.click()
    expect(page.get_by_text('Attempt 2', exact=False)).to_be_visible()
    for document in store.process(process_id)['documents']:
        item = store.document(document['id'])
        path = store.document_root(item) / 'transcript.txt'
        path.write_text('Narration fixture.')
        store.add_artifact(item['id'], 'transcript', path)
        store.update_document(item['id'], state='completed')
    page.reload()
    expect(page.get_by_role('heading', name='Ready when you are.')).to_be_visible()
    with page.expect_download() as result:
        page.get_by_role('link', name='Download all outputs').click()
    assert result.value.suggested_filename.endswith('.zip')
    page.screenshot(path=str(evidence / 'process-complete-desktop.png'), full_page=True)
    page.goto(url + '/admin')
    page.get_by_role('tab', name='Services').click()
    page.locator('#speaker').fill('Ryan')
    page.get_by_role('button', name='Save settings', exact=True).click()
    expect(page.locator('#notice')).to_have_text('Settings saved.')
    page.screenshot(path=str(evidence / 'services-desktop.png'), full_page=True)
    page.get_by_role('tab', name='Avatars').click()
    expect(page.locator('.avatar-card')).to_have_count(5)
    page.locator('.avatar-card img').evaluate_all("images => Promise.all(images.map(image => {image.loading='eager'; return image.decode();}))")
    page.screenshot(path=str(evidence / 'avatars-desktop.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(evidence / 'avatars-mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.goto(url + '/upload')
    expect(page.locator('#recent .recent-row')).to_have_count(1)
    page.screenshot(path=str(evidence / 'upload-mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert errors == []


def test_service_failure_and_drag_drop(web):
    page, app, url, root = web

    async def unavailable(settings):
        return {'ready': False, 'errors': ['TTS service is unavailable. Return later.']}

    app.state.health_check = unavailable
    page.goto(url + '/upload')
    data = pdf_file(root / 'Dropped.pdf').read_bytes()
    page.locator('#dropzone').evaluate('''(element, bytes) => {
        const transfer = new DataTransfer();
        transfer.items.add(new File([new Uint8Array(bytes)], 'Dropped.pdf', {type:'application/pdf'}));
        element.dispatchEvent(new DragEvent('drop', {bubbles:true,dataTransfer:transfer}));
    }''', list(data))
    expect(page.get_by_text('Dropped.pdf', exact=True)).to_be_visible()
    page.get_by_role('button', name='Convert documents').click()
    expect(page.locator('#upload-error')).to_contain_text('Return later.')
    assert app.state.store.processes() == []
    page.screenshot(path='/tmp/vnizer/p06/service-unavailable.png', full_page=True)


def test_authentication_and_avatar_admin(web):
    from PIL import Image

    page, app, url, root = web
    app.state.config.username = 'owner'
    app.state.config.password = 'secret'
    page.goto(url + '/upload')
    expect(page.get_by_role('button', name='Sign in', exact=True)).to_be_visible()
    page.get_by_label('Username').fill('owner')
    page.get_by_label('Password').fill('wrong')
    page.get_by_role('button', name='Sign in', exact=True).click()
    expect(page.locator('#login-error')).to_contain_text('incorrect')
    page.get_by_label('Password').fill('secret')
    page.get_by_role('button', name='Sign in', exact=True).click()
    expect(page.get_by_role('heading', name='Add your documents')).to_be_visible()
    page.goto(url + '/admin')
    page.get_by_role('tab', name='Avatars').click()
    path = root / 'guide.png'
    Image.new('RGB', (100, 100), 'teal').save(path)
    page.get_by_label('Name', exact=True).fill('Custom guide')
    page.get_by_label('Avatar file').set_input_files(path)
    page.get_by_role('button', name='Upload avatar').click()
    card = page.locator('.avatar-card').filter(has=page.get_by_role('heading', name='Custom guide'))
    expect(card).to_be_visible()
    card.get_by_role('button', name='Select', exact=True).click()
    expect(card.get_by_text('Selected', exact=True)).to_be_visible()
    page.on('dialog', lambda dialog: dialog.accept())
    card.get_by_role('button', name='Delete', exact=True).click()
    expect(card).to_have_count(0)
    page.get_by_role('button', name='Sign out').click()
    expect(page.get_by_role('button', name='Sign in', exact=True)).to_be_visible()


def test_admin_cancels_and_deletes_files_and_process(web):
    page, app, url, root = web
    page.goto(url + '/upload')
    expect(page.get_by_role('heading', name='Add your documents')).to_be_visible()
    page.locator('#pdf-files').set_input_files(pdf_file(root / 'Delete me.pdf'))
    page.get_by_role('button', name='Convert documents').click()
    expect(page.locator('.document')).to_have_count(1)
    process_id = page.url.rsplit('/', 1)[1]
    page.goto(url + '/admin')
    page.get_by_role('button', name='Stop', exact=True).click()
    expect(page.locator('.document .badge')).to_have_text('canceled')
    page.locator('summary').click()
    page.on('dialog', lambda dialog: dialog.accept())
    page.get_by_role('button', name='Delete file', exact=True).click()
    expect(page.locator('summary')).to_have_text('All artifacts (0)')
    page.get_by_role('button', name='Delete process', exact=True).click()
    expect(page.get_by_text('No processes yet.', exact=False)).to_be_visible()
    assert app.state.store.process(process_id) is None

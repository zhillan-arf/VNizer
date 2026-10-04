import io
import json
import math
import struct
import subprocess
import wave

import httpx
import pytest

from vnizer.avatars import seed_avatars, validate_avatar
from vnizer.media import render_document, wav_info
from vnizer.store import Store, new_id


def wav_bytes(seconds=0.5):
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"".join(struct.pack("<h", int(1000 * math.sin(i * 440 * math.tau / 24000)))
                                   for i in range(round(seconds * 24000))))
    return output.getvalue()


def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))


def media_document(tmp_path):
    store = Store(tmp_path)
    pid, did = new_id(), new_id()
    root = tmp_path / "processes" / pid / did
    root.mkdir(parents=True)
    source = root / "source.pdf"
    source.write_bytes(b"fixture")
    store.create_process(pid, [{"id": did, "name": "A research note.pdf", "pages": 1,
                               "path": source}], store.settings())
    store.update_document(did, stage="media", state="rendering")
    (root / "chunks.json").write_text(json.dumps({"chunks": [
        {"index": 0, "text": "The result is uncertain.", "mood": "serious", "page": 1},
        {"index": 1, "text": "More measurements are necessary.", "mood": "explaining", "page": 1},
    ]}))
    return store, store.document(did)


def test_outputs_have_expected_streams_and_speech_cache(tmp_path):
    store, document = media_document(tmp_path)
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, content=wav_bytes(), headers={"Content-Type": "audio/wav"})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        render_document(store, document, client)
        render_document(store, document, client)
    assert len(calls) == 2
    root = store.document_root(document)
    audio, video = probe(root / "audio.mp4"), probe(root / "video.mp4")
    assert [s["codec_type"] for s in audio["streams"]] == ["audio"]
    assert {s["codec_name"] for s in video["streams"]} == {"h264", "aac"}
    stream = next(s for s in video["streams"] if s["codec_type"] == "video")
    assert (stream["width"], stream["height"]) == (1280, 720)
    assert abs(float(video["format"]["duration"]) - 1) < 0.15
    assert (root / "render/000000-00/scene.png").exists()


def test_invalid_audio_is_not_published(tmp_path):
    store, document = media_document(tmp_path)
    with (httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"bad"))) as client,
          pytest.raises((wave.Error, EOFError))):
        render_document(store, document, client)
    assert not (store.document_root(document) / "audio.mp4").exists()


def test_truncated_wave_fails(tmp_path):
    path = tmp_path / "bad.wav"
    path.write_bytes(wav_bytes()[:-100])
    with pytest.raises(ValueError, match="truncated"):
        wav_info(path)


def test_initial_avatars_are_decodable(tmp_path):
    store = Store(tmp_path)
    seed_avatars(store)
    seed_avatars(store)
    with store.connect() as db:
        rows = db.execute("SELECT * FROM avatars").fetchall()
    assert len(rows) == 5
    for row in rows:
        validate_avatar(store.file_path(row["path"]))
        assert row["selected"]


def test_animated_avatar_preserves_alpha_and_renders(tmp_path):
    from PIL import Image

    from vnizer.avatars import add_avatar

    store, document = media_document(tmp_path)
    path = tmp_path / "animation.webp"
    first = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    second = first.copy()
    for image, color in ((first, "red"), (second, "blue")):
        from PIL import ImageDraw
        ImageDraw.Draw(image).rectangle((16, 16, 48, 48), fill=color)
    first.save(path, save_all=True, append_images=[second], duration=150, loop=0, lossless=True)
    avatar_id = add_avatar(store, path, "Animation fixture", "serious")
    with store.connect() as db:
        db.execute("UPDATE avatars SET selected=1 WHERE id=?", (avatar_id,))
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=wav_bytes()))) as client:
        render_document(store, document, client)
    assert (store.document_root(document) / "video.mp4").is_file()

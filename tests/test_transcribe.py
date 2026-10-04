import json

import httpx
import pymupdf
import pytest

from vnizer.chunks import chunk_text
from vnizer.store import Store, new_id
from vnizer.transcribe import normalize_response, transcribe


def response(text="Research results are uncertain.", mood="explaining", finish="stop"):
    return {"choices": [{"finish_reason": finish, "message": {"content": json.dumps({
        "blank": False, "warnings": [],
        "blocks": [{"role": "paragraph", "text": text, "mood": mood}],
    })}}]}


@pytest.mark.parametrize("text", [
    "A sentence. " * 150, "word " * 300, "x" * 1500,
    "你好，世界。" * 150, "αβγ " * 500,
    "Dr. Jones measured 3.14 units. The result was uncertain. " * 30,
])
def test_chunks_preserve_content_and_limit(text):
    chunks = chunk_text(text)
    assert all(0 < len(chunk) <= 512 for chunk in chunks)
    assert "".join("".join(chunks).split()) == "".join(text.split())


def test_sentence_and_comma_boundaries():
    first = "A" * 300 + "."
    second = "B" * 300 + "."
    assert chunk_text(first + " " + second) == [first, second]
    long = "word " * 65 + ", " + "word " * 65 + "."
    assert chunk_text(long)[0].endswith(",")
    assert chunk_text("Dr. Jones agrees. Next result.", 20) == ["Dr. Jones agrees.", "Next result."]


@pytest.mark.parametrize("body", [
    response(finish="length"), {"choices": []},
    {"choices": [{"finish_reason": "stop", "message": {"content": "not JSON"}}]},
    {"choices": [{"finish_reason": "stop", "message": {"content": '{"blank":false,"blocks":[],"warnings":[]}'}}]},
])
def test_invalid_responses_fail(body):
    with pytest.raises(ValueError):
        normalize_response(body)


def test_unknown_mood_has_warning():
    page = normalize_response(response(mood="angry"))
    assert page["blocks"][0]["mood"] == "neutral"
    assert page["warnings"]


def setup_document(tmp_path):
    store = Store(tmp_path)
    process_id, document_id = new_id(), new_id()
    source = tmp_path / "processes" / process_id / document_id / "source.pdf"
    source.parent.mkdir(parents=True)
    with pymupdf.open() as pdf:
        for text in ("Research methods.", "Results."):
            page = pdf.new_page()
            page.insert_text((50, 50), text)
        pdf.save(source)
    settings = store.settings()
    settings["ftt_model"] = "fixture"
    store.create_process(process_id, [{"id": document_id, "name": "paper.pdf", "pages": 2,
                                      "path": source}], settings)
    return store, store.claim()


def test_saved_pages_resume_after_failure(tmp_path):
    store, document = setup_document(tmp_path)
    calls = []

    def failed_second(request):
        payload = json.loads(request.content)
        calls.append(payload)
        if len(calls) == 2:
            return httpx.Response(200, json=response(finish="length"))
        return httpx.Response(200, json=response("The method uses two samples."))

    with (httpx.Client(transport=httpx.MockTransport(failed_second)) as client,
          pytest.raises(ValueError, match="incomplete")):
        transcribe(store, document, client)
    root = store.document_root(document)
    assert (root / "pages/00001.json").exists()
    assert (root / "pages/00002.raw.json").exists()
    assert not (root / "transcript.txt").exists()
    assert store.document(document["id"])["progress"] == 1
    resumed = []

    def success(request):
        resumed.append(json.loads(request.content))
        return httpx.Response(200, json=response("The result remains uncertain.", "serious"))

    with httpx.Client(transport=httpx.MockTransport(success)) as client:
        chunks = transcribe(store, document, client)
    assert len(resumed) == 1
    assert [c["page"] for c in chunks] == [1, 2]
    assert [c["mood"] for c in chunks] == ["explaining", "serious"]
    assert (root / "transcript.txt").read_text() == (
        "The method uses two samples.\n\nThe result remains uncertain.\n")
    assert store.document(document["id"])["stage"] == "media"
    assert len(list((root / "chunks").glob("*.txt"))) == 2
    assert "data:image/png;base64," in calls[0]["messages"][1]["content"][1]["image_url"]["url"]


def test_canceled_document_does_not_call_service(tmp_path):
    store, document = setup_document(tmp_path)
    store.cancel(document["process_id"])
    with (httpx.Client(transport=httpx.MockTransport(lambda request: pytest.fail("Unexpected request"))) as client,
          pytest.raises(InterruptedError)):
        transcribe(store, document, client)

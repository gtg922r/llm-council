from pathlib import Path

from fastapi.testclient import TestClient

import backend.config as config
import backend.main as main
from backend.application.prompt_builder import build_prompt_content
from backend.domain.models import FileAttachment
from backend.infrastructure.blob_store import LocalFileBlobStore
from backend.main import FileContext, SendMessageRequest
from backend import storage


def test_send_message_request_accepts_files():
    """SendMessageRequest should accept structured file context."""
    request = SendMessageRequest(
        content="hello",
        files=[FileContext(name="notes.txt", content="example", size=7)],
    )

    assert request.files[0].name == "notes.txt"
    assert request.files[0].content == "example"
    assert request.files[0].size == 7


def test_file_context_size_optional():
    """FileContext size is optional."""
    request = SendMessageRequest(
        content="hello",
        files=[FileContext(name="notes.txt", content="example")],
    )

    assert request.files[0].size is None


def test_storage_add_user_message_stores_blob_reference(tmp_path, monkeypatch):
    """Storage should store file content in blobs and persist only a reference."""
    conversations_dir = tmp_path / "conversations"
    blobs_dir = tmp_path / "blobs"
    monkeypatch.setattr(storage, "DATA_DIR", str(conversations_dir))
    monkeypatch.setattr(storage, "BLOB_DIR", str(blobs_dir))

    storage.create_conversation("conv-1")
    storage.add_user_message(
        "conv-1",
        "hello",
        files=[{"name": "notes.txt", "content": "example", "size": 7}],
    )

    conversation = storage.get_conversation("conv-1")
    msg = conversation["messages"][-1]
    assert msg["role"] == "user"
    assert msg["content"] == "hello"
    assert "files" in msg
    assert msg["files"][0]["name"] == "notes.txt"
    assert "reference_id" in msg["files"][0]
    assert "content" not in msg["files"][0]

    ref_id = msg["files"][0]["reference_id"]
    blob_path = blobs_dir / f"{ref_id}.txt"
    assert blob_path.exists()
    assert blob_path.read_text(encoding="utf-8") == "example"


def test_prompt_builder_resolves_blob_references(tmp_path):
    blobs = LocalFileBlobStore(tmp_path)
    ref = blobs.save_text("example")
    prompt = build_prompt_content(
        "hello",
        [FileAttachment(name="notes.txt", reference_id=ref)],
        blobs,
    )
    assert prompt == (
        "hello\n\n"
        "--- FILE: notes.txt ---\n"
        "example\n"
        "--- END FILE: notes.txt ---"
    )


def test_send_message_persists_assistant_metadata_and_blob_files(tmp_path, monkeypatch):
    """Full flow: API stores blob refs + persists assistant metadata on reload."""

    conversations_dir = tmp_path / "conversations"
    blobs_dir = tmp_path / "blobs"
    monkeypatch.setattr(config, "DATA_DIR", str(conversations_dir))
    monkeypatch.setattr(config, "BLOB_DIR", str(blobs_dir))

    # Make the council deterministic and fast for this test.
    monkeypatch.setattr(config, "COUNCIL_MODELS", ["test-model"])
    monkeypatch.setattr(config, "CHAIRMAN_MODEL", "test-chairman")

    class FakeLLM:
        async def chat(self, model, messages, *, timeout=None):
            prompt = messages[0]["content"]
            if "Generate a very short title" in prompt:
                return {"content": "Mock Title"}
            if "You are evaluating different responses" in prompt:
                return {"content": "Eval\n\nFINAL RANKING:\n1. Response A"}
            if "You are the Chairman of an LLM Council" in prompt:
                return {"content": "Final synthesis"}
            return {"content": "Stage 1 response"}

    client = TestClient(main.app)
    main.app.dependency_overrides[main.get_llm] = lambda: FakeLLM()
    conv = client.post("/api/conversations", json={}).json()

    payload = {"content": "hello", "files": [{"name": "notes.txt", "content": "example", "size": 7}]}
    resp = client.post(f"/api/conversations/{conv['id']}/message", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["stage3"]["response"] == "Final synthesis"
    assert body["metadata"]["label_to_model"] == {"Response A": "test-model"}
    assert body["metadata"]["anonymized_label_map"] == {"Response A": "test-model"}

    # Reload conversation: metadata should be persisted in the assistant message.
    reloaded = client.get(f"/api/conversations/{conv['id']}").json()
    assert reloaded["messages"][0]["role"] == "user"
    assert reloaded["messages"][0]["files"][0]["name"] == "notes.txt"
    assert "reference_id" in reloaded["messages"][0]["files"][0]
    assert "content" not in reloaded["messages"][0]["files"][0]

    assert reloaded["messages"][-1]["role"] == "assistant"
    assert reloaded["messages"][-1]["metadata"]["label_to_model"] == {"Response A": "test-model"}
    assert reloaded["messages"][-1]["metadata"]["aggregate_rankings"] != []

    # And the blob should exist.
    ref_id = reloaded["messages"][0]["files"][0]["reference_id"]
    assert (Path(blobs_dir) / f"{ref_id}.txt").exists()

    main.app.dependency_overrides.clear()

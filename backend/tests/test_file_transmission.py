import pytest

from backend.application.council_service import CouncilOrchestrator
from backend.application.prompt_builder import build_prompt_content
from backend.domain.models import FileAttachment
from backend.infrastructure.blob_store import LocalFileBlobStore
from backend.infrastructure.json_repository import JsonConversationRepository
from backend.main import FileContext, SendMessageRequest
from backend.ports import LLMProvider
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


def test_add_user_message_stores_files(tmp_path, monkeypatch):
    """Storage should persist file references (not raw content)."""
    conv_dir = tmp_path / "conversations"
    blob_dir = tmp_path / "blobs"
    monkeypatch.setattr(storage, "DATA_DIR", str(conv_dir))
    monkeypatch.setattr(storage, "DATA_BLOBS_DIR", str(blob_dir))
    storage.create_conversation("conv-1")
    files = [{"name": "notes.txt", "content": "example", "size": 7}]

    storage.add_user_message("conv-1", "hello", files=files)
    conversation = storage.get_conversation("conv-1")

    stored_files = conversation["messages"][-1]["files"]
    assert stored_files[0]["name"] == "notes.txt"
    assert stored_files[0]["size"] == 7
    assert "content" not in stored_files[0]
    assert "file_reference_id" in stored_files[0]
    assert storage.get_file_text(stored_files[0]["file_reference_id"]) == "example"


def test_build_prompt_content_appends_files(tmp_path):
    """Prompt builder should append file blocks after the user message."""
    blob_store = LocalFileBlobStore(str(tmp_path / "blobs"))
    ref1 = blob_store.save_text("example")
    ref2 = blob_store.save_text("- item")
    files = [
        FileAttachment(name="notes.txt", file_reference_id=ref1, size=7),
        FileAttachment(name="todo.md", file_reference_id=ref2, size=6),
    ]

    prompt = build_prompt_content(content="hello", files=files, blob_store=blob_store)

    assert prompt == (
        "hello\n\n"
        "--- FILE: notes.txt ---\n"
        "example\n"
        "--- END FILE: notes.txt ---\n\n"
        "--- FILE: todo.md ---\n"
        "- item\n"
        "--- END FILE: todo.md ---"
    )


def test_add_user_message_omits_files_when_none(tmp_path, monkeypatch):
    """Storage should omit files when none are provided."""
    conv_dir = tmp_path / "conversations"
    blob_dir = tmp_path / "blobs"
    monkeypatch.setattr(storage, "DATA_DIR", str(conv_dir))
    monkeypatch.setattr(storage, "DATA_BLOBS_DIR", str(blob_dir))
    storage.create_conversation("conv-1")

    storage.add_user_message("conv-1", "hello")
    conversation = storage.get_conversation("conv-1")

    assert "files" not in conversation["messages"][-1]


@pytest.mark.asyncio
async def test_orchestrator_uses_blob_resolved_file_content(tmp_path):
    """CouncilOrchestrator should build prompts from blob-stored file contents."""

    class RecordingLLM(LLMProvider):
        def __init__(self):
            self.calls: list[tuple[str, str]] = []  # (model, prompt)

        async def chat(self, *, model: str, messages: list[dict[str, str]], timeout: float | None = None):
            prompt = messages[0]["content"]
            self.calls.append((model, prompt))
            if model == "google/gemini-2.5-flash":
                return {"content": "Mock Title"}
            if model == "chairman":
                return {"content": "final"}
            # stage2 prompt includes the example "FINAL RANKING:" block
            if "FINAL RANKING:" in prompt and "Now provide your evaluation" in prompt:
                return {"content": "ok\n\nFINAL RANKING:\n1. Response A"}
            return {"content": "stage1 response"}

    repo = JsonConversationRepository(str(tmp_path / "conversations"))
    blob_store = LocalFileBlobStore(str(tmp_path / "blobs"))
    llm = RecordingLLM()
    service = CouncilOrchestrator(
        repo=repo,
        llm=llm,
        blob_store=blob_store,
        council_models=["council-1"],
        chairman_model="chairman",
    )

    repo.create("conv-1")

    async for _event in service.run(
        conversation_id="conv-1",
        content="hello",
        files=[{"name": "notes.txt", "content": "example", "size": 7}],
    ):
        pass

    stage1_prompts = [p for (m, p) in llm.calls if m == "council-1" and "Now provide your evaluation" not in p]
    assert stage1_prompts, "Expected at least one Stage 1 prompt call"
    assert "--- FILE: notes.txt ---" in stage1_prompts[0]
    assert "example" in stage1_prompts[0]

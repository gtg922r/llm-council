from fastapi.testclient import TestClient
import backend.main as main
import backend.infrastructure.blob_store as blob_store_module
import backend.application.council_service as council_service_module

def test_send_message_end_to_end_with_files(tmp_path, monkeypatch):
    """Posting a message with files should store files and format the prompt."""
    monkeypatch.setattr(main.repository, "data_dir", str(tmp_path))
    monkeypatch.setattr(blob_store_module, "BLOB_DIR", str(tmp_path / "blobs"))

    captured = []

    async def fake_query(model, messages, timeout=30.0):
        # We need to capture the prompt here
        if messages and messages[0]['role'] == 'user':
             captured.append(messages[0]['content'])
        return {"content": "ok\n\nFINAL RANKING:\n1. Response A"}

    monkeypatch.setattr(main.llm_provider, "query", fake_query)
    
    # Also patch generate_conversation_title
    async def fake_title(_content):
        return "Mock Title"
    monkeypatch.setattr(main, "generate_conversation_title", fake_title)
    
    # Patch COUNCIL_MODELS in service
    monkeypatch.setattr(council_service_module, "COUNCIL_MODELS", ["test-model"])

    client = TestClient(main.app)
    conv = client.post("/api/conversations", json={}).json()

    payload = {
        "content": "hello",
        "files": [{"name": "notes.txt", "content": "example", "size": 7}],
    }

    response = client.post(
        f"/api/conversations/{conv['id']}/message",
        json=payload,
    )

    assert response.status_code == 200
    
    assert "ok" in response.json()["stage3"]["response"]

    conversation = main.repository.get(conv["id"])
    assert len(conversation.messages[0].files) == 1
    assert conversation.messages[0].files[0].name == "notes.txt"
    assert conversation.messages[0].files[0].file_reference_id is not None
    
    # Check prompt construction
    # We captured multiple prompts (Stage 1, Stage 2, Stage 3)
    # The first one should be Stage 1 user prompt
    found = False
    for prompt in captured:
        if prompt.startswith("hello\n\n--- FILE: notes.txt ---"):
            found = True
            break
    assert found

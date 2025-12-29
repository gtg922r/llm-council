from fastapi.testclient import TestClient
from backend.main import app
import os
import shutil
from backend.storage import DATA_DIR, ensure_data_dir
from unittest.mock import patch, AsyncMock
import pytest
import json

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_data():
    """Setup a clean test data directory."""
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    ensure_data_dir()
    yield
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)

@patch('backend.main.run_full_council')
@patch('backend.main.generate_conversation_title')
def test_send_message_with_files_integrates_correctly(mock_title, mock_council):
    """Test that send_message integrates files into prompt and storage."""
    # Create conversation
    create_resp = client.post("/api/conversations", json={})
    conv_id = create_resp.json()["id"]
    
    # Mock responses
    mock_council.return_value = ([], [], {"response": "mocked"}, {})
    mock_title.return_value = "Test Conv"
    
    # Send message with files
    files = [
        {"name": "test.txt", "content": "hello"}
    ]
    resp = client.post(
        f"/api/conversations/{conv_id}/message", 
        json={
            "content": "Analyze this",
            "files": files
        }
    )
    
    assert resp.status_code == 200
    
    # Verify run_full_council was called with concatenated content
    # Expected content: "Analyze this\n\n--- FILE: test.txt ---\nhello\n--- END FILE: test.txt ---"
    expected_prompt = "Analyze this\n\n--- FILE: test.txt ---\nhello\n--- END FILE: test.txt ---"
    mock_council.assert_called_once_with(expected_prompt)
    
    # Verify storage has files
    from backend.storage import get_conversation
    conv = get_conversation(conv_id)
    assert "files" in conv["messages"][0]
    assert conv["messages"][0]["files"][0]["name"] == "test.txt"

@patch('backend.main.query_model')
@patch('backend.main.generate_conversation_title')
@patch('backend.main.stage3_synthesize_final')
def test_send_message_stream_with_files_integrates_correctly(mock_stage3, mock_title, mock_query):
    """Test that send_message_stream integrates files into prompt."""
    # Create conversation
    create_resp = client.post("/api/conversations", json={})
    conv_id = create_resp.json()["id"]
    
    # Mock
    mock_query.return_value = {"content": "mocked response"}
    mock_stage3.return_value = {"response": "final"}
    mock_title.return_value = "Title"
    
    # Send stream message
    files = [{"name": "f1.py", "content": "print(1)"}]
    
    # Use context manager for streaming
    with client.stream(
        "POST", 
        f"/api/conversations/{conv_id}/message/stream",
        json={"content": "Check code", "files": files}
    ) as response:
        assert response.status_code == 200
        # Consume the stream
        for line in response.iter_lines():
            pass

    # Verify query_model was called with concatenated prompt for Stage 1
    expected_prompt = "Check code\n\n--- FILE: f1.py ---\nprint(1)\n--- END FILE: f1.py ---"
    
    # query_model is called multiple times (once for each model in COUNCIL_MODELS for Stage 1, then for Stage 2)
    # We just check that at least one call in Stage 1 had the expected prompt.
    # Stage 1 calls look like: query_model(model, [{"role": "user", "content": expected_prompt}])
    
    found_correct_call = False
    for call in mock_query.call_args_list:
        args, kwargs = call
        # args[1] is messages list
        if args[1][0]["content"] == expected_prompt:
            found_correct_call = True
            break
    
    assert found_correct_call, "No call to query_model found with the concatenated prompt"

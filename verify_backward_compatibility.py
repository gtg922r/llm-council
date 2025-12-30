import httpx
import json
import time
import subprocess
import os
import shutil

def verify_backward_compatibility():
    print("Starting Backward Compatibility Verification...")
    
    # 1. Setup mock legacy conversation
    conv_id = "legacy-conv-123"
    os.makedirs("data/conversations", exist_ok=True)
    legacy_conv = {
        "id": conv_id,
        "created_at": "2025-01-01T12:00:00Z",
        "title": "Legacy Conversation",
        "is_pinned": False,
        "is_archived": False,
        "messages": [
            {
                "role": "user",
                "content": "Hello, this is a legacy message."
            },
            {
                "role": "assistant",
                "stage1": [],
                "stage2": [],
                "stage3": {"response": "I understand."}
            }
        ]
    }
    with open(f"data/conversations/{conv_id}.json", 'w') as f:
        json.dump(legacy_conv, f)
    print(f"Created legacy conversation: {conv_id}")

    # 2. Start Backend
    print("Starting backend...")
    proc = subprocess.Popen(["uv", "run", "python", "-m", "backend.main"], env={**os.environ, "PORT": "8002"})
    time.sleep(3)

    try:
        with httpx.Client(base_url="http://localhost:8002", timeout=10.0) as client:
            # 3. Retrieve Legacy Conversation
            print("Retrieving legacy conversation...")
            resp = client.get(f"/api/conversations/{conv_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["title"] == "Legacy Conversation"
            assert len(data["messages"]) == 2
            assert "files" not in data["messages"][0]
            print("Successfully retrieved legacy conversation.")

            # 4. Append New Message (with files) to Legacy Conversation
            print("Adding new message with files to legacy conversation...")
            files = [{"name": "new_file.txt", "content": "brand new content"}]
            resp = client.post(
                f"/api/conversations/{conv_id}/message",
                json={
                    "content": "What is in the new file?",
                    "files": files
                }
            )
            assert resp.status_code == 200
            print("Successfully added message with files to legacy conversation.")

            # 5. Verify Storage
            with open(f"data/conversations/{conv_id}.json", 'r') as f:
                stored_data = json.load(f)
                assert len(stored_data["messages"]) >= 3
                # The first message should still be without files
                assert "files" not in stored_data["messages"][0]
                # The latest user message should have files
                # It might be at index 2 if the assistant message was added
                user_msgs = [m for m in stored_data["messages"] if m["role"] == "user"]
                assert len(user_msgs) == 2
                assert "files" in user_msgs[1]
                print("Storage verification successful.")

        print("Backward Compatibility Verification PASSED!")
    finally:
        print("Stopping backend...")
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    verify_backward_compatibility()

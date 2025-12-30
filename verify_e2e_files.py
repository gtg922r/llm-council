import httpx
import json
import time
import subprocess
import os
import shutil

def verify_e2e():
    print("Starting E2E Verification...")
    
    # 1. Clean data dir
    if os.path.exists("data/conversations"):
        shutil.rmtree("data/conversations")
    os.makedirs("data/conversations", exist_ok=True)

    # 2. Start Backend
    print("Starting backend...")
    proc = subprocess.Popen(["uv", "run", "python", "-m", "backend.main"], env={**os.environ, "PORT": "8001"})
    time.sleep(3) # Wait for backend to start

    try:
        # 3. Create Conversation
        print("Creating conversation...")
        with httpx.Client(base_url="http://localhost:8001", timeout=60.0) as client:
            resp = client.post("/api/conversations", json={})
            assert resp.status_code == 200
            conv_id = resp.json()["id"]
            print(f"Created conversation: {conv_id}")

            # 4. Send Message with Files
            print("Sending message with files...")
            files = [
                {"name": "test.txt", "content": "This is a test file content.", "size": 28}
            ]
            resp = client.post(
                f"/api/conversations/{conv_id}/message",
                json={
                    "content": "What is in the attached file?",
                    "files": files
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            print("Received response from Stage 3")
            assert "stage3" in data
            assert data["stage3"]["response"] is not None

            # 5. Verify Storage
            print("Verifying storage...")
            storage_file = f"data/conversations/{conv_id}.json"
            assert os.path.exists(storage_file)
            with open(storage_file, 'r') as f:
                stored_data = json.load(f)
                messages = stored_data["messages"]
                assert len(messages) >= 2 # User + Assistant
                user_msg = messages[0]
                assert user_msg["role"] == "user"
                assert "files" in user_msg
                assert user_msg["files"][0]["name"] == "test.txt"
                print("Storage verification successful.")

        print("E2E Verification PASSED!")
    finally:
        print("Stopping backend...")
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    verify_e2e()

from fastapi.testclient import TestClient

import backend.main as main
from backend import storage


def test_has_unread_is_set_on_assistant_message_and_can_be_cleared(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main.storage, "DATA_DIR", str(tmp_path))

    async def fake_run_full_council(_prompt_content):
        return [], [], {"response": "ok"}, {}

    monkeypatch.setattr(main, "run_full_council", fake_run_full_council)

    client = TestClient(main.app)
    conv = client.post("/api/conversations", json={}).json()

    # New conversations default to not unread.
    assert conv["has_unread"] is False

    resp = client.post(f"/api/conversations/{conv['id']}/message", json={"content": "hello"})
    assert resp.status_code == 200

    after = client.get(f"/api/conversations/{conv['id']}").json()
    assert after["has_unread"] is True

    cleared = client.patch(f"/api/conversations/{conv['id']}", json={"has_unread": False}).json()
    assert cleared["has_unread"] is False

    listed = client.get("/api/conversations").json()
    assert listed[0]["id"] == conv["id"]
    assert listed[0]["has_unread"] is False


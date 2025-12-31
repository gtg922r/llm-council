import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
from backend.domain.models import (
    Conversation, 
    UserMessage, 
    AssistantMessage, 
    MessageRole,
    Attachment,
    AssistantMetadata
)

def test_user_message_creation():
    msg = UserMessage(content="Hello")
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello"
    assert msg.files == []

def test_user_message_with_attachments():
    att = Attachment(filename="test.txt", content_type="text/plain", file_reference_id="ref123")
    msg = UserMessage(content="Check this", files=[att])
    assert len(msg.files) == 1
    assert msg.files[0].file_reference_id == "ref123"

def test_assistant_message_creation():
    # Minimal assistant message
    msg = AssistantMessage(
        stage1=[],
        stage2=[],
        stage3={"model": "test-model", "response": "test-response"},
        metadata=AssistantMetadata(label_to_model={}, aggregate_rankings=[])
    )
    assert msg.role == MessageRole.ASSISTANT
    assert msg.stage3["response"] == "test-response"

def test_conversation_creation():
    conv = Conversation(
        id="conv123",
        created_at=datetime.now(timezone.utc),
        messages=[
            UserMessage(content="Hi"),
            AssistantMessage(
                stage1=[],
                stage2=[],
                stage3={"model": "m", "response": "r"},
                metadata=AssistantMetadata(label_to_model={}, aggregate_rankings=[])
            )
        ]
    )
    assert conv.id == "conv123"
    assert len(conv.messages) == 2
    assert isinstance(conv.messages[0], UserMessage)
    assert isinstance(conv.messages[1], AssistantMessage)

def test_invalid_role():
    from backend.domain.models import Message
    with pytest.raises(ValidationError):
        Message(role="invalid")

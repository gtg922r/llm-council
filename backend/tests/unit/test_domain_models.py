"""Unit tests for domain models."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestDomainModels:
    """Tests for the domain models."""

    def test_stage1_response_creation(self):
        """Test that Stage1Response can be created with model, response, and status."""
        from backend.domain.models import Stage1Response
        
        response = Stage1Response(
            model="openai/gpt-4o",
            response="This is a test response.",
            status="success"
        )
        
        assert response.model == "openai/gpt-4o"
        assert response.response == "This is a test response."
        assert response.status == "success"

    def test_stage1_response_error_status(self):
        """Test Stage1Response with error status."""
        from backend.domain.models import Stage1Response
        
        response = Stage1Response(
            model="openai/gpt-4o",
            response="Error: Failed to get response.",
            status="error"
        )
        
        assert response.status == "error"

    def test_stage2_ranking_creation(self):
        """Test that Stage2Ranking can be created with model, ranking text, and parsed ranking."""
        from backend.domain.models import Stage2Ranking
        
        ranking = Stage2Ranking(
            model="openai/gpt-4o",
            ranking="Response A is best...\n\nFINAL RANKING:\n1. Response A\n2. Response B",
            parsed_ranking=["Response A", "Response B"],
            status="success"
        )
        
        assert ranking.model == "openai/gpt-4o"
        assert ranking.ranking.startswith("Response A")
        assert ranking.parsed_ranking == ["Response A", "Response B"]
        assert ranking.status == "success"

    def test_stage3_synthesis_creation(self):
        """Test that Stage3Synthesis can be created."""
        from backend.domain.models import Stage3Synthesis
        
        synthesis = Stage3Synthesis(
            model="google/gemini-2.5-pro",
            response="The council has determined..."
        )
        
        assert synthesis.model == "google/gemini-2.5-pro"
        assert synthesis.response == "The council has determined..."

    def test_council_metadata_creation(self):
        """Test that CouncilMetadata stores label_to_model and aggregate_rankings."""
        from backend.domain.models import CouncilMetadata, AggregateRanking
        
        metadata = CouncilMetadata(
            label_to_model={"Response A": "openai/gpt-4o", "Response B": "anthropic/claude-3"},
            aggregate_rankings=[
                AggregateRanking(model="openai/gpt-4o", average_rank=1.5, rankings_count=2),
                AggregateRanking(model="anthropic/claude-3", average_rank=2.5, rankings_count=2),
            ]
        )
        
        assert metadata.label_to_model["Response A"] == "openai/gpt-4o"
        assert len(metadata.aggregate_rankings) == 2
        assert metadata.aggregate_rankings[0].average_rank == 1.5

    def test_user_message_creation(self):
        """Test that UserMessage can be created with content."""
        from backend.domain.models import UserMessage
        
        message = UserMessage(content="What is the meaning of life?")
        
        assert message.role == "user"
        assert message.content == "What is the meaning of life?"
        assert message.files is None

    def test_user_message_with_files(self):
        """Test UserMessage with file attachments."""
        from backend.domain.models import UserMessage, FileAttachment
        
        message = UserMessage(
            content="Please analyze this code",
            files=[FileAttachment(name="main.py", content="print('hello')", size=16)]
        )
        
        assert len(message.files) == 1
        assert message.files[0].name == "main.py"
        assert message.files[0].content == "print('hello')"

    def test_file_attachment_with_blob_reference(self):
        """Test FileAttachment with blob reference instead of inline content."""
        from backend.domain.models import FileAttachment
        
        # Create attachment with blob reference
        attachment = FileAttachment(
            name="large_file.py",
            size=100000,
            blob_reference_id="abc123-uuid"
        )
        
        assert attachment.name == "large_file.py"
        assert attachment.content is None
        assert attachment.blob_reference_id == "abc123-uuid"
        assert attachment.is_blob_reference is True

    def test_file_attachment_inline_is_not_blob_reference(self):
        """Test that inline FileAttachment is not marked as blob reference."""
        from backend.domain.models import FileAttachment
        
        attachment = FileAttachment(
            name="small_file.py",
            content="print('small')",
            size=14
        )
        
        assert attachment.is_blob_reference is False
        assert attachment.content == "print('small')"

    def test_assistant_message_creation_with_metadata(self):
        """Test that AssistantMessage stores all stages and metadata."""
        from backend.domain.models import (
            AssistantMessage, Stage1Response, Stage2Ranking, 
            Stage3Synthesis, CouncilMetadata, AggregateRanking
        )
        
        stage1 = [Stage1Response(model="model1", response="resp1", status="success")]
        stage2 = [Stage2Ranking(model="model1", ranking="rank1", parsed_ranking=["Response A"], status="success")]
        stage3 = Stage3Synthesis(model="chairman", response="final answer")
        metadata = CouncilMetadata(
            label_to_model={"Response A": "model1"},
            aggregate_rankings=[AggregateRanking(model="model1", average_rank=1.0, rankings_count=1)]
        )
        
        message = AssistantMessage(
            stage1=stage1,
            stage2=stage2,
            stage3=stage3,
            metadata=metadata
        )
        
        assert message.role == "assistant"
        assert len(message.stage1) == 1
        assert message.metadata.label_to_model["Response A"] == "model1"

    def test_assistant_message_metadata_persistence(self):
        """Test that metadata is preserved when serializing and deserializing."""
        from backend.domain.models import (
            AssistantMessage, Stage1Response, Stage2Ranking, 
            Stage3Synthesis, CouncilMetadata, AggregateRanking
        )
        
        metadata = CouncilMetadata(
            label_to_model={"Response A": "openai/gpt-4o"},
            aggregate_rankings=[AggregateRanking(model="openai/gpt-4o", average_rank=1.0, rankings_count=1)]
        )
        
        message = AssistantMessage(
            stage1=[Stage1Response(model="openai/gpt-4o", response="test", status="success")],
            stage2=[Stage2Ranking(model="openai/gpt-4o", ranking="test", parsed_ranking=["Response A"], status="success")],
            stage3=Stage3Synthesis(model="chairman", response="final"),
            metadata=metadata
        )
        
        # Serialize to dict and back
        message_dict = message.model_dump()
        restored = AssistantMessage.model_validate(message_dict)
        
        assert restored.metadata.label_to_model["Response A"] == "openai/gpt-4o"
        assert restored.metadata.aggregate_rankings[0].average_rank == 1.0

    def test_conversation_creation(self):
        """Test that Conversation can be created."""
        from backend.domain.models import Conversation, UserMessage
        
        conversation = Conversation(
            id="test-123",
            title="Test Conversation"
        )
        
        assert conversation.id == "test-123"
        assert conversation.title == "Test Conversation"
        assert len(conversation.messages) == 0
        assert conversation.is_pinned is False
        assert conversation.is_archived is False

    def test_conversation_with_messages(self):
        """Test Conversation with messages."""
        from backend.domain.models import (
            Conversation, UserMessage, AssistantMessage,
            Stage1Response, Stage2Ranking, Stage3Synthesis
        )
        
        user_msg = UserMessage(content="Hello")
        assistant_msg = AssistantMessage(
            stage1=[Stage1Response(model="m1", response="r1", status="success")],
            stage2=[],
            stage3=Stage3Synthesis(model="chairman", response="final")
        )
        
        conversation = Conversation(
            id="test-456",
            title="Test",
            messages=[user_msg, assistant_msg]
        )
        
        assert len(conversation.messages) == 2
        assert conversation.messages[0].role == "user"
        assert conversation.messages[1].role == "assistant"

    def test_conversation_serialization(self):
        """Test that Conversation serializes and deserializes correctly."""
        from backend.domain.models import (
            Conversation, UserMessage, AssistantMessage,
            Stage1Response, Stage2Ranking, Stage3Synthesis,
            CouncilMetadata, AggregateRanking
        )
        
        metadata = CouncilMetadata(
            label_to_model={"Response A": "model1"},
            aggregate_rankings=[AggregateRanking(model="model1", average_rank=1.0, rankings_count=1)]
        )
        
        conversation = Conversation(
            id="test-789",
            title="Serialization Test",
            messages=[
                UserMessage(content="Test query"),
                AssistantMessage(
                    stage1=[Stage1Response(model="model1", response="answer", status="success")],
                    stage2=[Stage2Ranking(model="model1", ranking="rank", parsed_ranking=["Response A"], status="success")],
                    stage3=Stage3Synthesis(model="chairman", response="synthesis"),
                    metadata=metadata
                )
            ]
        )
        
        # Serialize to JSON and back
        json_str = conversation.model_dump_json()
        restored = Conversation.model_validate_json(json_str)
        
        assert restored.id == "test-789"
        assert len(restored.messages) == 2
        
        # Check metadata persisted correctly
        assistant_msg = restored.messages[1]
        assert assistant_msg.metadata is not None
        assert assistant_msg.metadata.label_to_model["Response A"] == "model1"


class TestCouncilRun:
    """Tests for the CouncilRun model which represents a complete council workflow."""

    def test_council_run_creation(self):
        """Test that CouncilRun can be created with all stage results."""
        from backend.domain.models import (
            CouncilRun, Stage1Response, Stage2Ranking, 
            Stage3Synthesis, CouncilMetadata, AggregateRanking
        )
        
        run = CouncilRun(
            user_query="What is 2+2?",
            stage1=[Stage1Response(model="m1", response="4", status="success")],
            stage2=[Stage2Ranking(model="m1", ranking="rank", parsed_ranking=["Response A"], status="success")],
            stage3=Stage3Synthesis(model="chairman", response="The answer is 4"),
            metadata=CouncilMetadata(
                label_to_model={"Response A": "m1"},
                aggregate_rankings=[AggregateRanking(model="m1", average_rank=1.0, rankings_count=1)]
            )
        )
        
        assert run.user_query == "What is 2+2?"
        assert len(run.stage1) == 1
        assert run.stage3.response == "The answer is 4"
        assert run.metadata.label_to_model["Response A"] == "m1"

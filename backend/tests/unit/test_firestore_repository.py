"""Tests for FirestoreConversationRepository.

These tests use the Firebase emulator for realistic testing.
Run with: firebase emulators:exec --only firestore,auth "pytest backend/tests/unit/test_firestore_repository.py -v"
"""

import os
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

# Set emulator environment before importing Firebase modules
os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
os.environ['FIREBASE_AUTH_EMULATOR_HOST'] = 'localhost:9099'

from backend.domain.models import (
    Conversation, 
    UserMessage, 
    AssistantMessage,
    Stage1Result,
    Stage2Result,
    AssistantMetadata,
    AggregateRanking
)


class TestFirestoreRepositorySerialization:
    """Test serialization/deserialization without actual Firestore."""
    
    def test_message_to_dict_user_message(self):
        """Test converting UserMessage to dict."""
        from backend.infrastructure.firestore_repository import FirestoreConversationRepository
        
        # Mock Firebase initialization
        with patch('backend.infrastructure.firestore_repository.get_firebase_app'):
            with patch('backend.infrastructure.firestore_repository.firestore'):
                repo = FirestoreConversationRepository.__new__(FirestoreConversationRepository)
                repo._db = MagicMock()
                
                msg = UserMessage(content="Hello", files=[])
                result = repo._message_to_dict(msg)
                
                assert result['role'] == 'user'
                assert result['content'] == 'Hello'
                assert result['files'] == []
    
    def test_message_to_dict_assistant_message_with_stage1(self):
        """Test converting AssistantMessage with Stage1Results to dict."""
        from backend.infrastructure.firestore_repository import FirestoreConversationRepository
        
        with patch('backend.infrastructure.firestore_repository.get_firebase_app'):
            with patch('backend.infrastructure.firestore_repository.firestore'):
                repo = FirestoreConversationRepository.__new__(FirestoreConversationRepository)
                repo._db = MagicMock()
                
                msg = AssistantMessage(
                    stage1=[
                        Stage1Result(model="gpt-4", response="Hello", status="success"),
                        Stage1Result(model="claude", response="Hi", status="success")
                    ],
                    stage2=[],
                    stage3={}
                )
                result = repo._message_to_dict(msg)
                
                assert result['role'] == 'assistant'
                assert len(result['stage1']) == 2
                assert result['stage1'][0]['model'] == 'gpt-4'
                assert result['stage1'][0]['response'] == 'Hello'
                assert isinstance(result['stage1'][0], dict)  # Not a Pydantic model
    
    def test_message_to_dict_assistant_message_with_all_stages(self):
        """Test converting AssistantMessage with all stages to dict."""
        from backend.infrastructure.firestore_repository import FirestoreConversationRepository
        
        with patch('backend.infrastructure.firestore_repository.get_firebase_app'):
            with patch('backend.infrastructure.firestore_repository.firestore'):
                repo = FirestoreConversationRepository.__new__(FirestoreConversationRepository)
                repo._db = MagicMock()
                
                msg = AssistantMessage(
                    stage1=[
                        Stage1Result(model="gpt-4", response="Hello", status="success")
                    ],
                    stage2=[
                        Stage2Result(
                            model="gpt-4", 
                            ranking="1. Response A", 
                            parsed_ranking=["Response A"],
                            status="success"
                        )
                    ],
                    stage3={"model": "gpt-4", "response": "Final answer"},
                    metadata=AssistantMetadata(
                        label_to_model={"Response A": "gpt-4"},
                        aggregate_rankings=[
                            AggregateRanking(model="gpt-4", average_rank=1.0, rankings_count=1)
                        ]
                    )
                )
                result = repo._message_to_dict(msg)
                
                assert result['role'] == 'assistant'
                assert len(result['stage1']) == 1
                assert len(result['stage2']) == 1
                assert result['stage3']['model'] == 'gpt-4'
                assert result['metadata']['label_to_model']['Response A'] == 'gpt-4'
    
    def test_message_to_dict_handles_none_stages(self):
        """Test that None stages are handled properly."""
        from backend.infrastructure.firestore_repository import FirestoreConversationRepository
        
        with patch('backend.infrastructure.firestore_repository.get_firebase_app'):
            with patch('backend.infrastructure.firestore_repository.firestore'):
                repo = FirestoreConversationRepository.__new__(FirestoreConversationRepository)
                repo._db = MagicMock()
                
                # Create message with explicit empty values
                msg = AssistantMessage(
                    stage1=[],
                    stage2=[],
                    stage3={}
                )
                result = repo._message_to_dict(msg)
                
                assert result['stage1'] == []
                assert result['stage2'] == []
                assert result['stage3'] == {}
    
    def test_dict_to_conversation_handles_none_stages(self):
        """Test that loading None stages from Firestore works."""
        from backend.infrastructure.firestore_repository import FirestoreConversationRepository
        
        with patch('backend.infrastructure.firestore_repository.get_firebase_app'):
            with patch('backend.infrastructure.firestore_repository.firestore'):
                repo = FirestoreConversationRepository.__new__(FirestoreConversationRepository)
                repo._db = MagicMock()
                
                # Simulate what Firestore might return (None values)
                doc_dict = {
                    'id': 'test-123',
                    'created_at': '2024-01-01T00:00:00',
                    'title': 'Test',
                    'is_pinned': False,
                    'is_archived': False,
                    'has_unread': False,
                    'messages': [
                        {'role': 'user', 'content': 'Hello', 'files': []},
                        {
                            'role': 'assistant',
                            'stage1': None,  # This could be None in Firestore
                            'stage2': None,
                            'stage3': None,
                            'metadata': None
                        }
                    ]
                }
                
                conv = repo._dict_to_conversation(doc_dict)
                
                assert conv.id == 'test-123'
                assert len(conv.messages) == 2
                assert conv.messages[1].stage1 == []
                assert conv.messages[1].stage2 == []
                assert conv.messages[1].stage3 == {}
    
    def test_dict_to_conversation_with_full_data(self):
        """Test loading a full conversation from Firestore format."""
        from backend.infrastructure.firestore_repository import FirestoreConversationRepository
        
        with patch('backend.infrastructure.firestore_repository.get_firebase_app'):
            with patch('backend.infrastructure.firestore_repository.firestore'):
                repo = FirestoreConversationRepository.__new__(FirestoreConversationRepository)
                repo._db = MagicMock()
                
                doc_dict = {
                    'id': 'test-123',
                    'created_at': '2024-01-01T00:00:00',
                    'title': 'Test Conversation',
                    'is_pinned': True,
                    'is_archived': False,
                    'has_unread': True,
                    'messages': [
                        {'role': 'user', 'content': 'What is 2+2?', 'files': []},
                        {
                            'role': 'assistant',
                            'stage1': [
                                {'model': 'gpt-4', 'response': '4', 'status': 'success'}
                            ],
                            'stage2': [
                                {'model': 'gpt-4', 'ranking': '1. A', 'parsed_ranking': ['A'], 'status': 'success'}
                            ],
                            'stage3': {'model': 'gpt-4', 'response': 'The answer is 4'},
                            'metadata': {
                                'label_to_model': {'A': 'gpt-4'},
                                'aggregate_rankings': [{'model': 'gpt-4', 'average_rank': 1.0, 'rankings_count': 1}]
                            }
                        }
                    ]
                }
                
                conv = repo._dict_to_conversation(doc_dict)
                
                assert conv.id == 'test-123'
                assert conv.title == 'Test Conversation'
                assert conv.is_pinned == True
                assert conv.has_unread == True
                assert len(conv.messages) == 2
                
                assistant_msg = conv.messages[1]
                assert len(assistant_msg.stage1) == 1
                assert assistant_msg.stage3['response'] == 'The answer is 4'
    
    def test_roundtrip_serialization(self):
        """Test that conversation survives serialization roundtrip."""
        from backend.infrastructure.firestore_repository import FirestoreConversationRepository
        
        with patch('backend.infrastructure.firestore_repository.get_firebase_app'):
            with patch('backend.infrastructure.firestore_repository.firestore'):
                repo = FirestoreConversationRepository.__new__(FirestoreConversationRepository)
                repo._db = MagicMock()
                
                # Create a full conversation
                original = Conversation(
                    id='test-roundtrip',
                    created_at=datetime(2024, 1, 1, 12, 0, 0),
                    title='Roundtrip Test',
                    is_pinned=True,
                    is_archived=False,
                    has_unread=True,
                    messages=[
                        UserMessage(content='Test query', files=[]),
                        AssistantMessage(
                            stage1=[Stage1Result(model='gpt-4', response='Answer', status='success')],
                            stage2=[Stage2Result(model='gpt-4', ranking='1. A', parsed_ranking=['A'], status='success')],
                            stage3={'model': 'gpt-4', 'response': 'Final'},
                            metadata=AssistantMetadata(
                                label_to_model={'A': 'gpt-4'},
                                aggregate_rankings=[AggregateRanking(model='gpt-4', average_rank=1.0, rankings_count=1)]
                            )
                        )
                    ]
                )
                
                # Serialize to dict (what would be saved to Firestore)
                serialized = repo._conversation_to_dict(original)
                
                # Deserialize back (what would be loaded from Firestore)
                restored = repo._dict_to_conversation(serialized)
                
                # Verify key fields match
                assert restored.id == original.id
                assert restored.title == original.title
                assert restored.is_pinned == original.is_pinned
                assert restored.has_unread == original.has_unread
                assert len(restored.messages) == len(original.messages)
                
                # Check user message
                assert restored.messages[0].content == original.messages[0].content
                
                # Check assistant message
                assert len(restored.messages[1].stage1) == 1
                assert restored.messages[1].stage3['response'] == 'Final'

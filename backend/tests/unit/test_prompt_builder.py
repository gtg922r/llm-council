from unittest.mock import patch, MagicMock
from backend.application.prompt_builder import build_prompt_content
from backend.domain.models import Attachment
from backend.infrastructure.blob_store import BlobStore

def test_build_prompt_content_resolves_blobs(tmp_path):
    blob_dir = tmp_path / "blobs"
    store = BlobStore(blob_dir=str(blob_dir))
    
    # Save a blob
    content = "File content in blob"
    ref_id = store.save_text(content)
    
    # Create attachment reference
    att = Attachment(filename="test.txt", file_reference_id=ref_id)
    
    # Mock BlobStore in application.prompt_builder
    with patch("backend.application.prompt_builder.BlobStore") as mock_store_class:
        mock_instance = MagicMock()
        mock_instance.get_text.return_value = content
        mock_store_class.return_value = mock_instance
        
        prompt = build_prompt_content("Hello", [att])
        
        assert "--- FILE: test.txt ---" in prompt
        assert content in prompt
        mock_instance.get_text.assert_called_with(ref_id)

def test_build_prompt_content_with_legacy_dict():
    prompt = build_prompt_content("Hello", [{"name": "old.txt", "content": "old content"}])
    assert "--- FILE: old.txt ---" in prompt
    assert "old content" in prompt

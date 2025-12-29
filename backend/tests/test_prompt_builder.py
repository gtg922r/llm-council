from backend.main import build_prompt_content, FileContext

def test_build_prompt_content_no_files():
    """Test that build_prompt_content returns just the message if no files are provided."""
    content = "Hello world"
    result = build_prompt_content(content, None)
    assert result == "Hello world"
    
    result = build_prompt_content(content, [])
    assert result == "Hello world"

def test_build_prompt_content_with_files():
    """Test that build_prompt_content correctly formats files."""
    content = "Analyze these files"
    files = [
        FileContext(name="test.txt", content="file context here"),
        FileContext(name="config.py", content="DEBUG=True", size=10)
    ]
    
    result = build_prompt_content(content, files)
    
    expected = (
        "Analyze these files\n\n"
        "--- FILE: test.txt ---\n"
        "file context here\n"
        "--- END FILE: test.txt ---\n\n"
        "--- FILE: config.py ---\n"
        "DEBUG=True\n"
        "--- END FILE: config.py ---"
    )
    assert result == expected
"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "openai/gpt-5.2",
    "google/gemini-3-pro-preview",
    # "anthropic/claude-sonnet-4.5",
    "anthropic/claude-opus-4.5",
    "x-ai/grok-4",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "google/gemini-3-pro-preview"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directories
# - Conversations: JSON metadata + message references
# - Blobs: large file attachments stored out-of-line
DATA_CONVERSATIONS_DIR = os.getenv("DATA_CONVERSATIONS_DIR", "data/conversations")
DATA_BLOBS_DIR = os.getenv("DATA_BLOBS_DIR", "data/blobs")

# Backwards-compatibility alias (older code/tests may still import DATA_DIR).
DATA_DIR = DATA_CONVERSATIONS_DIR

# Environment detection
IS_CODESPACE = os.getenv("CODESPACES") == "true"
DEBUG_MODE = os.getenv("DEBUG") == "true"

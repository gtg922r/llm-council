"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "google/gemini-2.5-flash-lite",
    "google/gemini-2.5-flash",
    "x-ai/grok-4.1-fast",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "google/gemini-3-flash-preview"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Environment detection
IS_CODESPACE = os.getenv("CODESPACES") == "true"
DEBUG_MODE = os.getenv("DEBUG") == "true"

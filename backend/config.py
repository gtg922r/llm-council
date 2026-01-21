"""Configuration for Symposia."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Model configurations for different modes
# Smart mode: Top-tier, most capable models
SMART_COUNCIL_MODELS = [
    "openai/gpt-5.2",
    "google/gemini-3-pro-preview",
    "anthropic/claude-opus-4.5",
    "x-ai/grok-4",
]
SMART_CHAIRMAN_MODEL = "google/gemini-3-pro-preview"

# Fast mode: Quick, cost-effective models
FAST_COUNCIL_MODELS = [
    "google/gemini-2.5-flash-lite",
    "anthropic/claude-3.5-haiku",
    "openai/gpt-4.1-nano",
    "meta-llama/llama-4-scout",
]
FAST_CHAIRMAN_MODEL = "google/gemini-2.5-flash-lite"

# Default models (backwards compatibility)
COUNCIL_MODELS = SMART_COUNCIL_MODELS
CHAIRMAN_MODEL = SMART_CHAIRMAN_MODEL

def get_models_for_mode(mode: str = "smart"):
    """Get council and chairman models based on mode.
    
    Args:
        mode: Either 'fast' or 'smart'
        
    Returns:
        Tuple of (council_models, chairman_model)
    """
    if mode == "fast":
        return FAST_COUNCIL_MODELS, FAST_CHAIRMAN_MODEL
    return SMART_COUNCIL_MODELS, SMART_CHAIRMAN_MODEL

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Environment detection
IS_CODESPACE = os.getenv("CODESPACES") == "true"
DEBUG_MODE = os.getenv("DEBUG") == "true"

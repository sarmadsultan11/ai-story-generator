"""
Free AI API client (Groq) — OpenAI-compatible, no paid OpenAI billing required.

Get a free key: https://console.groq.com/keys
"""

import os

from openai import OpenAI

# Groq offers a free tier and uses the same OpenAI SDK pattern
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def get_api_key() -> str:
    return os.getenv("GROQ_API_KEY", "").strip()


def get_model() -> str:
    return os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def get_ai_client() -> OpenAI:
    api_key = get_api_key()
    if not api_key or api_key.startswith("gsk_your"):
        raise ValueError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your free Groq key."
        )
    return OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)

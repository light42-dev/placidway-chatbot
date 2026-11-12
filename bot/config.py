"""Settings, read from the environment (and from .env when running locally)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    """Read KEY=value lines without overriding variables that are already set."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_env_file(ROOT / ".env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# Groq models, tried in order. Each has its own daily token allowance on the
# free tier (200,000 tokens, about 90 replies), so the later ones keep replies
# fast when the first runs out.
GROQ_MODELS = [name.strip() for name in os.environ.get(
    "GROQ_MODELS", "qwen/qwen3.8-27b,openai/gpt-oss-120b,openai/gpt-oss-20b").split(",") if name.strip()]
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

LLM_TIMEOUT_S = 20          # per provider call
MAX_OUTPUT_TOKENS = 700     # room for the answer plus any hidden reasoning tokens
MAX_INPUT_CHARS = 4000      # a longer user message is rejected with HTTP 413
MAX_HISTORY_MESSAGES = 8    # older messages are dropped to protect the token budget
MAX_HISTORY_CHARS = 600     # each kept earlier message is cut to this length
CONTEXT_CHARS = 4200        # total size of the passages given to the model
RATE_LIMIT_REQUESTS = 8     # per session (or client IP) ...
RATE_LIMIT_WINDOW_S = 10    # ... in any 10 seconds; more get HTTP 429
REPLY_CACHE_TTL_S = 30      # an identical conversation within this time is answered from memory

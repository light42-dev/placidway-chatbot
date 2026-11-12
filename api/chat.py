"""Vercel entry point for POST /api/chat. All logic lives in the bot package."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.web import ChatHandler  # noqa: E402


class handler(ChatHandler):
    """Vercel looks for a class with this exact name."""

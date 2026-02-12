"""Web chat UI entry point for `falk chat`.

Exposes `app` for uvicorn so the chat server works regardless of working directory.
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Load .env early so Pydantic AI can see LLM API keys and LLM_MODEL
_env_candidates = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",  # project root when dev
]
for _p in _env_candidates:
    if _p.exists():
        load_dotenv(_p, override=True)
        break
else:
    load_dotenv(override=True)

from falk import build_web_app

app = build_web_app()

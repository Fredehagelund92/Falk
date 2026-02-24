"""Local web UI for testing the data agent (Pydantic AI built-in UI).

Run::

    uv run uvicorn app.web:app --reload

Requires:  ``uv sync``

Note: Always use ``uv run`` to ensure the package is found. If you get
``ModuleNotFoundError: No module named 'falk'``, make sure you've run
``uv sync`` from the project root.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Load .env early so Pydantic AI can see LLM API keys
_env_candidates = [Path(__file__).resolve().parent.parent / ".env", Path.cwd() / ".env"]
for _p in _env_candidates:
    if _p.exists():
        load_dotenv(_p, override=True)
        break
else:
    load_dotenv(override=True)


# Lazy import to avoid importing pydantic_ai at module level
# Lazy import for better error messages
def _get_app():
    from falk import build_web_app
    from falk.agent import DataAgent
    from falk.llm.state import get_session_store

    # Initialize DataAgent once and pass to web app
    try:
        core = DataAgent()
    except Exception as e:
        raise RuntimeError(
            f"Cannot start web UI - DataAgent initialization failed: {e}\n"
            "Check your falk_project.yaml, semantic_models.yaml, and database connection."
        ) from e

    # Validate session config at startup (fail fast if postgres misconfigured)
    try:
        get_session_store()
    except ValueError as e:
        raise RuntimeError(
            f"Cannot start web UI - session config invalid: {e}\n"
            "Set session.store=memory in falk_project.yaml, or set POSTGRES_URL in .env for postgres."
        ) from e

    return build_web_app(core=core)


# ASGI app — delegates to the library's PydanticAI agent.
app = _get_app()

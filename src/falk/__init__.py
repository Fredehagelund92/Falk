"""falk — semantic-metric data agent library.

Core modules
------------
agent.py              DataAgent core (BSL + all data methods)
llm.py                Pydantic AI Agent with tool definitions
prompt.py             System prompt construction
settings.py           Configuration (env vars, paths)
cli.py                Project management CLI
validation.py         Project validation and testing
observability/        LangFuse tracing and feedback
tools/                Core functionality (warehouse, semantic, charts, calculations)
evals/                Test framework for agent validation

Application interfaces (app/ — thin wrappers)
----------------------------------------------
app/web.py            Local web UI
app/slack.py          Slack bot (socket mode + markdown converter)
app/mcp.py            MCP server (FastMCP)

Public API
----------
- ``DataAgent``    — core class (BSL models + metrics)
- ``build_agent``  — Pydantic AI Agent wired to DataAgent
- ``build_web_app`` — ASGI app for local testing
"""

from falk.agent import DataAgent, SemanticMetadata
from falk.session import (
    SessionStore,
    MemorySessionStore,
    RedisSessionStore,
    create_session_store,
)

# Lazy imports — llm module requires the optional `pydantic-ai` package.


def build_agent():  # noqa: D103
    from falk.llm import build_agent as _build
    return _build()


def build_web_app():  # noqa: D103
    from falk.llm import build_web_app as _build
    return _build()


__all__ = [
    "DataAgent",
    "SemanticMetadata",
    "build_agent",
    "build_web_app",
    "SessionStore",
    "MemorySessionStore",
    "RedisSessionStore",
    "create_session_store",
]

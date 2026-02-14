"""falk — semantic-metric data agent library.

Core modules
------------
settings.py           Configuration (env vars, paths)
agent.py              DataAgent core (BSL models + metric listing)
prompt.py             System-prompt template + auto-generation from BSL metadata
pydantic_agent.py     Pydantic AI Agent with tool definitions
feedback.py           Feedback collection (Slack → LangFuse)
langfuse_integration.py  LangFuse observability and tracing
cli.py                Project management CLI
validation.py         Project validation and testing
mcp/                  MCP server (FastMCP) for external clients
tools/                Core functionality (warehouse, semantic, charts, calculations)
evals/                Test framework for agent validation

Application interfaces (app/ — thin wrappers)
----------------------------------------------
app/web.py            Local web UI (Pydantic AI built-in)
app/slack.py          Slack bot (socket mode)

Public API
----------
- ``DataAgent``    — core class (BSL models + metrics)
- ``build_agent``  — Pydantic AI Agent wired to DataAgent
- ``build_web_app`` — ASGI app for local testing
"""

from falk.agent import DataAgent

# Lazy imports — pydantic_agent requires the optional `pydantic-ai` package.


def build_agent():  # noqa: D103
    from falk.pydantic_agent import build_agent as _build
    return _build()


def build_web_app():  # noqa: D103
    from falk.pydantic_agent import build_web_app as _build
    return _build()


__all__ = ["DataAgent", "build_agent", "build_web_app"]

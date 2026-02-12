"""falk — semantic-metric data agent library (BSL + DuckDB).

File guide
----------
settings.py           Configuration (env vars, paths)
agent.py              DataAgent core (BSL models from YAML + metric listing)
prompt.py             System-prompt template + auto-generation from BSL metadata
pydantic_agent.py     Pydantic AI Agent with tool definitions (main entry point)
feedback.py           Emoji-reaction feedback collection (LangFuse)
langfuse_integration.py  LangFuse observability and tracing (optional)
tools/warehouse.py    BSL-backed query execution
tools/semantic.py     Semantic-model info lookups (from BSL models)
tools/calculations.py Analytics helpers (shares, deltas, date ranges)
tools/charts.py       Plotly chart generation

Entry points (app/ — thin wrappers, not part of the library)
-------------------------------------------------------------
app/web.py            Local web UI (Pydantic AI built-in, uvicorn)
app/slack.py          Slack bot (socket mode) — primary production interface
app/mcp_server.py     MCP server for exploring agent configuration

Public API
----------
- ``DataAgent``    — core class (no LLM, just BSL models + metrics)
- ``build_agent``  — Pydantic AI Agent wired to DataAgent (requires ``pydantic-ai``)
- ``build_web_app`` — ASGI app via ``Agent.to_web()`` for local testing
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

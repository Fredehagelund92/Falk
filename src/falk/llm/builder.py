"""Agent/web app construction helpers."""

from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent, ModelSettings

from falk.agent import DataAgent
from falk.llm.tools import data_tools, load_custom_toolsets, readiness_probe
from falk.observability import configure_observability
from falk.prompt import build_system_prompt


def _get_model() -> str:
    """Resolve LLM model from falk_project.yaml (agent.provider, agent.model)."""
    from falk.settings import load_settings

    s = load_settings()
    provider = (s.agent.provider or "openai").lower()
    model = s.agent.model or "gpt-5-mini"
    if provider == "anthropic":
        return f"anthropic:{model}"
    if provider == "google" or provider == "google-genai":
        return f"google-genai:{model}"
    return f"openai:{model}"


def _make_history_processor(max_messages: int):
    """Return a history processor that keeps only the last N messages."""

    def keep_recent(messages: list) -> list:
        return messages[-max_messages:] if len(messages) > max_messages else messages

    return keep_recent


def build_agent() -> Agent[DataAgent, str]:
    """Build the Pydantic AI agent with DataAgent as deps."""
    from falk.settings import load_settings

    configure_observability()
    core = DataAgent()
    s = load_settings()
    system_prompt = build_system_prompt(
        core.bsl_models,
        metadata=core.metadata,
        agent_config=s.agent,
        project_root=s.project_root,
    )
    max_msgs = s.advanced.message_history_max_messages
    history_processors = [_make_history_processor(max_msgs)] if (max_msgs and max_msgs > 0) else []
    custom_toolsets = load_custom_toolsets(s.project_root, s.agent.extensions_tools)
    return Agent(
        model=_get_model(),
        deps_type=DataAgent,
        toolsets=[data_tools, *custom_toolsets],
        system_prompt=system_prompt,
        output_type=str,
        model_settings=ModelSettings(
            max_tokens=s.advanced.max_tokens,
            temperature=s.advanced.temperature,
            timeout=float(s.advanced.model_timeout_seconds),
        ),
        retries=max(1, int(s.advanced.max_retries)),
        tool_timeout=float(s.advanced.query_timeout_seconds),
        history_processors=history_processors,
    )


def build_web_app(core: DataAgent | None = None):
    """Return ASGI app for local web UI. Always returns a FastAPI host app.

    The host app registers health, ready, stream, and charts routes, then mounts
    the agent's to_web() ASGI app (which may be Starlette or FastAPI) for any
    additional routes. This avoids include_router failures when to_web() returns
    Starlette.
    """
    from fastapi import APIRouter, FastAPI
    from fastapi.responses import JSONResponse
    from starlette.staticfiles import StaticFiles

    if core is None:
        core = DataAgent()

    web_agent = build_agent()
    agent_app = web_agent.to_web(deps=core)

    host_app = FastAPI(title="falk web API")

    health_router = APIRouter()

    @health_router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @health_router.get("/ready")
    async def ready():
        payload = readiness_probe(core)
        return JSONResponse(payload, status_code=200 if payload["ready"] else 503)

    host_app.include_router(health_router)

    charts_dir = Path.cwd() / "exports" / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    host_app.mount("/charts", StaticFiles(directory=str(charts_dir)), name="charts")

    host_app.mount("/", agent_app)
    return host_app

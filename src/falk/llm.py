"""Pydantic AI conversational agent — tools, system prompt, build_agent, build_web_app.

This module provides the LLM-powered agent that wraps DataAgent. It defines all
tools (query_metric, list_metrics, export, etc.) and wires them to the
BSL-backed DataAgent core.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic_ai import Agent, FunctionToolset, ModelSettings, RunContext

from falk.agent import DataAgent
from falk.prompt import build_system_prompt
from falk.session import create_session_store
from falk.tools.calculations import compute_shares, period_date_ranges
from falk.tools.semantic import get_semantic_model_info
from falk.tools.warehouse import (
    lookup_dimension_values,
    run_warehouse_query,
)
from falk.access import (
    allowed_dimensions,
    allowed_metrics,
    filter_dimensions,
    filter_metrics,
    is_dimension_allowed,
    is_metric_allowed,
)

# ---------------------------------------------------------------------------
# Toolset — all tools receive RunContext[DataAgent], ctx.deps = DataAgent
# ---------------------------------------------------------------------------

data_tools = FunctionToolset()


# ---------------------------------------------------------------------------
# Per-session state for multi-user support (Slack threads, web sessions)
# ---------------------------------------------------------------------------

# Session store: pluggable backend (memory or Redis) configured via falk_project.yaml
# Each session holds: last_query_data, last_query_metric, last_query_aggregate, pending_files
_session_store = create_session_store()


def _session_id(ctx: RunContext[DataAgent]) -> str:
    """Compute session ID from context metadata."""
    if not ctx.metadata:
        return "default"
    thread_ts = ctx.metadata.get("thread_ts")
    if thread_ts:
        return str(thread_ts)
    channel = ctx.metadata.get("channel")
    user_id = ctx.metadata.get("user_id")
    if channel and user_id:
        return f"{channel}:{user_id}"
    if user_id:
        return str(user_id)
    return "default"


def _get_session_state(ctx: RunContext[DataAgent]) -> dict[str, Any]:
    """Get or create session state for the current context."""
    sid = _session_id(ctx)
    state = _session_store.get(sid)
    if not state:
        state = {
            "last_query_data": [],
            "last_query_metric": None,
            "last_query_aggregate": None,
            "pending_files": [],
        }
        _session_store.set(sid, state)
    return state


def _user_id(ctx: RunContext[DataAgent]) -> str | None:
    """Safely extract user_id from context metadata."""
    return ctx.metadata.get("user_id") if ctx.metadata else None


def _access_cfg(ctx: RunContext[DataAgent]) -> "AccessConfig":
    """Return the AccessConfig from the agent's settings."""
    from falk.settings import AccessConfig  # noqa: F401 (type-only, imported for hint)
    return ctx.deps._settings.access


def get_pending_files_for_session(session_id: str) -> list[dict[str, Any]]:
    """Get pending files for a specific session (for Slack upload)."""
    state = _session_store.get(session_id)
    if state:
        return state.get("pending_files", [])
    return []


def clear_pending_files_for_session(session_id: str) -> None:
    """Clear pending files for a specific session (after Slack upload)."""
    state = _session_store.get(session_id)
    if state:
        state["pending_files"] = []
        _session_store.set(session_id, state)


@data_tools.tool
def list_metrics(ctx: RunContext[DataAgent]) -> dict[str, Any]:
    """List all available metrics grouped by semantic model."""
    result = ctx.deps.list_metrics()
    allowed = allowed_metrics(_user_id(ctx), _access_cfg(ctx))
    result["metrics"] = filter_metrics(result["metrics"], allowed)
    return result


@data_tools.tool
def list_dimensions(ctx: RunContext[DataAgent]) -> dict[str, Any]:
    """List all available dimensions across semantic models."""
    result = ctx.deps.list_dimensions()
    allowed = allowed_dimensions(_user_id(ctx), _access_cfg(ctx))
    result["dimensions"] = filter_dimensions(result["dimensions"], allowed)
    return result


@data_tools.tool
def describe_metric(ctx: RunContext[DataAgent], name: str) -> str:
    """Get full description of a metric (measure) including dimensions and time grains."""
    allowed = allowed_metrics(_user_id(ctx), _access_cfg(ctx))
    if not is_metric_allowed(name, allowed):
        return f"Metric '{name}' not found. Use list_metrics to see available metrics."
    return ctx.deps.describe_metric(name)


@data_tools.tool
def describe_model(ctx: RunContext[DataAgent], name: str) -> dict[str, Any] | str:
    """Get full description of a semantic model (metrics, dimensions, time grains)."""
    return ctx.deps.describe_model(name)


@data_tools.tool
def describe_dimension(ctx: RunContext[DataAgent], name: str) -> str:
    """Get full description of a dimension (type, description, domain)."""
    return ctx.deps.describe_dimension(name)


@data_tools.tool
def lookup_values(
    ctx: RunContext[DataAgent],
    dimension: str,
    search: str | None = None,
) -> list[str] | str:
    """Look up actual values for a dimension (fuzzy search). Use before filtering."""
    allowed = allowed_dimensions(_user_id(ctx), _access_cfg(ctx))
    if not is_dimension_allowed(dimension, allowed):
        return f"Dimension '{dimension}' not found."
    result = ctx.deps.lookup_dimension_values(dimension, search)
    values = result.get("values", [])
    if values is None:
        return f"Dimension '{dimension}' not found."
    if not values:
        return f"No values found for '{dimension}'" + (f" matching '{search}'" if search else "") + "."
    return values[:100]


def _matches_concept(item: dict, concept: str) -> bool:
    """Case-insensitive substring match on name, display_name, or synonyms."""
    c = concept.lower().strip()
    if not c:
        return False
    name = (item.get("name") or "").lower()
    display = (item.get("display_name") or "").lower()
    if c in name or c in display:
        return True
    for syn in (item.get("synonyms") or []):
        if c in str(syn).lower():
            return True
    return False


@data_tools.tool
def disambiguate(
    ctx: RunContext[DataAgent],
    entity_type: str,
    concept: str,
) -> dict[str, Any] | str:
    """Find metrics or dimensions matching a concept (name or synonym).
    Use when the user's request is ambiguous — returns candidates so you can ask:
    'Which did you mean: A (description), B (description)?'"""
    et = (entity_type or "").strip().lower()
    c = (concept or "").strip()
    if not c:
        return "Concept cannot be empty."
    if et not in ("metric", "dimension"):
        return f"entity_type must be 'metric' or 'dimension', got '{entity_type}'."

    allowed_m = allowed_metrics(_user_id(ctx), _access_cfg(ctx))
    allowed_d = allowed_dimensions(_user_id(ctx), _access_cfg(ctx))

    if et == "metric":
        items = ctx.deps.list_metrics().get("metrics", [])
        items = filter_metrics(items, allowed_m)
    else:
        items = ctx.deps.list_dimensions().get("dimensions", [])
        items = filter_dimensions(items, allowed_d)

    matches = [
        {
            "name": m.get("name"),
            "display_name": m.get("display_name") or m.get("name"),
            "description": (m.get("description") or "").strip() or None,
        }
        for m in items
        if _matches_concept(m, c)
    ]
    if not matches:
        return f"No {et}s found for '{concept}'."
    return {"matches": matches}


@data_tools.tool
def query_metric(
    ctx: RunContext[DataAgent],
    metrics: list[str],
    group_by: list[str] | None = None,
    time_grain: str | None = None,
    filters: list[dict[str, Any]] | None = None,
    order: str | None = None,
    limit: int | None = None,
) -> dict[str, Any] | str:
    """Query one or more metrics with optional group_by, filters, time_grain, order, limit."""
    allowed_m = allowed_metrics(_user_id(ctx), _access_cfg(ctx))
    allowed_d = allowed_dimensions(_user_id(ctx), _access_cfg(ctx))

    for m in metrics:
        if not is_metric_allowed(m, allowed_m):
            return f"Metric '{m}' is not available. Use list_metrics to see available metrics."
    for d in (group_by or []):
        if not is_dimension_allowed(d, allowed_d):
            return f"Dimension '{d}' is not available. Use list_dimensions to see available dimensions."
    for f in (filters or []):
        field_name = f.get("field") or f.get("dimension")
        if field_name and not is_dimension_allowed(field_name, allowed_d):
            return f"Dimension '{field_name}' is not available for filtering."

    state = _get_session_state(ctx)
    result = run_warehouse_query(
        core=ctx.deps,
        metrics=metrics,
        dimensions=group_by,
        filters=filters,
        time_grain=time_grain,
        limit=limit,
        order_by=order,
    )
    if not result.ok:
        return f"Query failed: {result.error}"
    state["last_query_data"] = result.data or []
    state["last_query_metric"] = result.metrics
    state["last_query_aggregate"] = getattr(result, "aggregate", None)
    _session_store.set(_session_id(ctx), state)
    return {
        "ok": True,
        "data": state["last_query_data"],
        "rows": len(state["last_query_data"]),
        "sql": getattr(result, "sql", None),
    }


@data_tools.tool
def compare_periods(
    ctx: RunContext[DataAgent],
    metric: str,
    period: str = "month",
    group_by: list[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any] | str:
    """Compare metric for current vs previous period (week, month, quarter)."""
    allowed_m = allowed_metrics(_user_id(ctx), _access_cfg(ctx))
    allowed_d = allowed_dimensions(_user_id(ctx), _access_cfg(ctx))

    if not is_metric_allowed(metric, allowed_m):
        return f"Metric '{metric}' is not available. Use list_metrics to see available metrics."
    for d in (group_by or []):
        if not is_dimension_allowed(d, allowed_d):
            return f"Dimension '{d}' is not available. Use list_dimensions to see available dimensions."

    state = _get_session_state(ctx)
    (cur_start, cur_end), (prev_start, prev_end) = period_date_ranges(period)
    date_filters_cur = [
        {"field": "date", "op": ">=", "value": cur_start},
        {"field": "date", "op": "<=", "value": cur_end},
    ]
    date_filters_prev = [
        {"field": "date", "op": ">=", "value": prev_start},
        {"field": "date", "op": "<=", "value": prev_end},
    ]
    cur_result = run_warehouse_query(
        core=ctx.deps,
        metrics=[metric],
        dimensions=group_by or [],
        filters=date_filters_cur,
        limit=limit,
    )
    prev_result = run_warehouse_query(
        core=ctx.deps,
        metrics=[metric],
        dimensions=group_by or [],
        filters=date_filters_prev,
        limit=limit,
    )
    if not cur_result.ok:
        return f"Current period query failed: {cur_result.error}"
    if not prev_result.ok:
        return f"Previous period query failed: {prev_result.error}"
    cur_data = cur_result.data or []
    prev_data = prev_result.data or []
    from falk.tools.calculations import compute_deltas
    group_keys = group_by or []
    if not group_keys and cur_data:
        group_keys = [k for k in cur_data[0].keys() if k != metric and k != "date"]
    # Grand total (no group_by): group_keys=[] is valid — compute_deltas still compares the single rows
    deltas = compute_deltas(cur_data, prev_data, metric, group_keys) if (cur_data or prev_data) else []
    state["last_query_data"] = deltas if deltas else cur_data
    state["last_query_metric"] = metric
    # Do NOT set last_query_aggregate (computed deltas, not a single BSL query)
    _session_store.set(_session_id(ctx), state)
    return {"ok": True, "data": deltas, "period": period}


@data_tools.tool
def compute_share(ctx: RunContext[DataAgent]) -> dict[str, Any] | str:
    """Add share_pct (percentage of total) to the last query result."""
    state = _get_session_state(ctx)
    if not state["last_query_data"] or not state["last_query_metric"]:
        return "No previous query. Run query_metric first."
    metric = state["last_query_metric"][0] if isinstance(state["last_query_metric"], list) else state["last_query_metric"]
    enriched = compute_shares(state["last_query_data"], metric)
    state["last_query_data"] = enriched
    _session_store.set(_session_id(ctx), state)
    return {"ok": True, "data": enriched}


@data_tools.tool
def export(ctx: RunContext[DataAgent], format: str = "csv") -> str:
    """Export the last query result. format: csv | excel | sheets.
    csv and excel write to exports/; sheets requires additional setup."""
    state = _get_session_state(ctx)
    if not state["last_query_data"]:
        return "No data to export. Run query_metric first."
    fmt = (format or "csv").strip().lower()
    if fmt == "csv":
        try:
            import csv
            export_dir = Path.cwd() / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = export_dir / f"export_{ts}.csv"
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(state["last_query_data"][0].keys()))
                writer.writeheader()
                writer.writerows(state["last_query_data"])
            state["pending_files"].append({"path": str(path), "title": path.name})
            _session_store.set(_session_id(ctx), state)
            return f"Exported {len(state['last_query_data'])} rows to {path}"
        except Exception as e:
            return f"Export failed: {e}"
    if fmt == "excel":
        try:
            import pandas as pd
            export_dir = Path.cwd() / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = export_dir / f"export_{ts}.xlsx"
            df = pd.DataFrame(state["last_query_data"])
            df.to_excel(path, index=False)
            state["pending_files"].append({"path": str(path), "title": path.name})
            _session_store.set(_session_id(ctx), state)
            return f"Exported {len(state['last_query_data'])} rows to {path}"
        except ImportError:
            return "Excel export requires openpyxl. Install with: uv sync"
        except Exception as e:
            return f"Export failed: {e}"
    if fmt == "sheets":
        return "Google Sheets export requires additional setup. Use export(format='csv') or export(format='excel') for now."
    return f"Unknown format '{format}'. Use csv, excel, or sheets."


@data_tools.tool
def generate_chart(ctx: RunContext[DataAgent]) -> str:
    """Generate a chart from the last query result using BSL's auto-detection.
    Chart type is inferred from the data dimensions. In Slack the chart is uploaded to the channel;
    in web UI the file path is returned."""
    state = _get_session_state(ctx)
    if not state["last_query_data"] or not state["last_query_metric"]:
        return "No data to chart. Run query_metric first."
    if not state["last_query_aggregate"]:
        return "No BSL aggregate available. Run query_metric with group_by first."
    
    try:
        # BSL auto-detects chart type and returns PNG bytes
        chart_bytes = state["last_query_aggregate"].chart(backend="plotly", format="png")
        if not chart_bytes:
            return "No dimension to chart. Run query_metric with group_by first."
        
        # Write to exports/charts/
        from datetime import datetime
        export_dir = Path.cwd() / "exports" / "charts"
        export_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        metric_ref = state["last_query_metric"]
        display_metric = metric_ref[0] if isinstance(metric_ref, list) else metric_ref
        path = export_dir / f"{display_metric}_{ts}.png"
        path.write_bytes(chart_bytes)
        
        state["pending_files"].append({"path": str(path), "title": path.name})
        _session_store.set(_session_id(ctx), state)
        
        # Slack: chart uploaded via pending_files; return short message
        # Web UI: return path
        if ctx.metadata and ctx.metadata.get("interface") == "slack":
            return f"Here's your chart for {display_metric}."
        return f"Chart saved to {path}"
    except Exception as e:
        return f"Chart generation failed: {e}"


# ---------------------------------------------------------------------------
# Build agent
# ---------------------------------------------------------------------------

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


def build_agent() -> Agent[DataAgent, str]:
    """Build the Pydantic AI agent with DataAgent as deps."""
    core = DataAgent()
    from falk.settings import load_settings
    s = load_settings()
    agent_config = s.agent
    project_root = s.project_root
    system_prompt = build_system_prompt(
        core.bsl_models,
        metadata=core.metadata,
        agent_config=agent_config,
        project_root=project_root,
    )
    agent = Agent(
        model=_get_model(),
        deps_type=DataAgent,
        toolsets=[data_tools],
        system_prompt=system_prompt,
        output_type=str,
        model_settings=ModelSettings(
            max_tokens=s.advanced.max_tokens,
            temperature=s.advanced.temperature,
            timeout=float(s.advanced.model_timeout_seconds),
        ),
        retries=max(1, int(s.advanced.max_retries)),
        tool_timeout=float(s.advanced.query_timeout_seconds),
    )
    return agent


def build_web_app(core: DataAgent | None = None):
    """Return ASGI app for local web UI (Agent.to_web).
    
    Args:
        core: Optional DataAgent instance to reuse. If None, creates a new one.
    """
    from starlette.staticfiles import StaticFiles

    if core is None:
        core = DataAgent()
    
    agent = build_agent()
    app = agent.to_web(deps=core)

    # Mount charts dir (file paths returned when inline display not supported)
    charts_dir = Path.cwd() / "exports" / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/charts", StaticFiles(directory=str(charts_dir)), name="charts")

    return app

"""Pydantic AI conversational agent — tools, system prompt, build_agent, build_web_app.

This module provides the LLM-powered agent that wraps DataAgent. It defines all
tools (query_metric, list_metrics, export_to_csv, etc.) and wires them to the
BSL-backed DataAgent core.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, FunctionToolset, RunContext

from falk.agent import DataAgent
from falk.prompt import build_system_prompt
from falk.tools.calculations import compute_shares, period_date_ranges
from falk.tools.charts import (
    generate_bar_chart,
    generate_line_chart,
    generate_pie_chart,
    suggest_chart_type,
)
from falk.tools.semantic import get_semantic_model_info
from falk.tools.warehouse import (
    lookup_dimension_values,
    run_warehouse_query,
    decompose_metric_change,
)

# ---------------------------------------------------------------------------
# Toolset — all tools receive RunContext[DataAgent], ctx.deps = DataAgent
# ---------------------------------------------------------------------------

data_tools = FunctionToolset()


# Module-level state for "last query result" and "pending files" (for Slack uploads)
_last_query_data: list[dict[str, Any]] = []
_last_query_metric: str | None = None
_pending_files: list[dict[str, Any]] = []


def _get_pending_files() -> list[dict[str, Any]]:
    return _pending_files


@data_tools.tool
def list_metrics(ctx: RunContext[DataAgent]) -> dict[str, Any]:
    """List all available metrics grouped by semantic model."""
    return ctx.deps.list_metrics()


@data_tools.tool
def list_dimensions(ctx: RunContext[DataAgent]) -> dict[str, Any]:
    """List all available dimensions across semantic models."""
    all_dims: list[dict[str, Any]] = []
    for model_name, model in ctx.deps.bsl_models.items():
        for dim_name, dim in model.get_dimensions().items():
            desc = ctx.deps.dimension_descriptions.get((model_name, dim_name), "") or ""
            dom = ctx.deps.dimension_domains.get((model_name, dim_name), "") or ""
            all_dims.append({
                "name": dim_name,
                "description": desc,
                "domain": dom,
                "type": "time" if getattr(dim, "is_time_dimension", False) else "categorical",
            })
    return {"dimensions": all_dims}


def _format_describe_metric(name: str, description: str, dimensions: list, time_grains: list) -> str:
    """Format metric description as prose."""
    dim_str = ", ".join(d.name for d in dimensions) if dimensions else "none"
    grains_str = ", ".join(time_grains) if time_grains else "none"
    return f"**{name}** — {description}. Dimensions: {dim_str}. Time grains: {grains_str}."


@data_tools.tool
def describe_metric(ctx: RunContext[DataAgent], name: str) -> str:
    """Get full description of a metric (measure) including dimensions and time grains."""
    info = get_semantic_model_info(
        ctx.deps.bsl_models,
        name,
        ctx.deps.model_descriptions,
    )
    if not info:
        return f"Metric '{name}' not found. Use list_metrics to see available metrics."
    return _format_describe_metric(
        name, info.description, info.dimensions, info.time_grains
    )


@data_tools.tool
def describe_model(ctx: RunContext[DataAgent], name: str) -> dict[str, Any] | str:
    """Get full description of a semantic model (metrics, dimensions, time grains)."""
    info = get_semantic_model_info(
        ctx.deps.bsl_models,
        name,
        ctx.deps.model_descriptions,
    )
    if not info:
        return f"Model '{name}' not found. Use list_metrics to see available models."
    dims = [{"name": d.name, "type": d.type, "description": d.description} for d in info.dimensions]
    return {
        "name": name,
        "description": info.description,
        "dimensions": dims,
        "metrics": info.metrics,
        "time_grains": info.time_grains,
    }


def _format_describe_dimension(name: str, description: str, domain: str, dim_type: str) -> str:
    """Format dimension description as prose."""
    lead = f"**{name}**"
    if description:
        lead += f" — {description}"
    lead += f". Type: {dim_type}."
    if domain:
        lead += f" Domain: {domain}."
    return lead


@data_tools.tool
def describe_dimension(ctx: RunContext[DataAgent], name: str) -> str:
    """Get full description of a dimension (type, description, domain)."""
    found: dict[str, Any] | None = None
    for model_name, model in ctx.deps.bsl_models.items():
        for dim_name, dim in model.get_dimensions().items():
            if dim_name == name:
                desc = ctx.deps.dimension_descriptions.get((model_name, dim_name), "") or ""
                dom = ctx.deps.dimension_domains.get((model_name, dim_name), "") or ""
                found = {
                    "name": dim_name,
                    "description": desc,
                    "domain": dom,
                    "type": "time" if getattr(dim, "is_time_dimension", False) else "categorical",
                }
                break
        if found:
            break
    if not found:
        return f"Dimension '{name}' not found. Use list_dimensions to see available dimensions."
    return _format_describe_dimension(
        found["name"], found["description"], found["domain"], found["type"]
    )


@data_tools.tool
def lookup_values(
    ctx: RunContext[DataAgent],
    dimension: str,
    search: str | None = None,
) -> list[str] | str:
    """Look up actual values for a dimension (fuzzy search). Use before filtering."""
    values = lookup_dimension_values(
        ctx.deps.bsl_models,
        dimension,
        search=search,
    )
    if values is None:
        return f"Dimension '{dimension}' not found."
    if not values:
        return f"No values found for '{dimension}'" + (f" matching '{search}'" if search else "") + "."
    return values[:100]  # Limit for token economy


@data_tools.tool
def query_metric(
    ctx: RunContext[DataAgent],
    metric: str,
    group_by: list[str] | None = None,
    time_grain: str | None = None,
    filters: list[dict[str, Any]] | None = None,
    order: str | None = None,
    limit: int | None = None,
) -> dict[str, Any] | str:
    """Query a metric with optional group_by, filters, time_grain, order, limit."""
    global _last_query_data, _last_query_metric
    filters_dict = None
    if filters:
        filters_dict = {}
        for f in filters:
            if isinstance(f, dict):
                dim = f.get("dimension") or f.get("field")
                op = (f.get("op") or f.get("operator", "=")).strip().upper()
                val = f.get("value")
                if dim and val is not None:
                    if op == "IN" and isinstance(val, list):
                        filters_dict[dim] = val
                    else:
                        filters_dict[dim] = val
    result = run_warehouse_query(
        core=ctx.deps,
        metric=metric,
        dimensions=group_by,
        filters=filters_dict,
        time_grain=time_grain,
        limit=limit,
        order_by=order,
    )
    if not result.ok:
        return f"Query failed: {result.error}"
    _last_query_data = result.data or []
    _last_query_metric = metric
    return {"ok": True, "data": _last_query_data, "rows": len(_last_query_data)}


@data_tools.tool
def compare_periods(
    ctx: RunContext[DataAgent],
    metric: str,
    period: str = "month",
    group_by: list[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any] | str:
    """Compare metric for current vs previous period (week, month, quarter)."""
    global _last_query_data, _last_query_metric
    (cur_start, cur_end), (prev_start, prev_end) = period_date_ranges(period)
    cur_result = run_warehouse_query(
        core=ctx.deps,
        metric=metric,
        dimensions=group_by or [],
        filters={"date": {"gte": cur_start, "lte": cur_end}},
        limit=limit,
    )
    prev_result = run_warehouse_query(
        core=ctx.deps,
        metric=metric,
        dimensions=group_by or [],
        filters={"date": {"gte": prev_start, "lte": prev_end}},
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
    _last_query_data = deltas if deltas else cur_data
    _last_query_metric = metric
    return {"ok": True, "data": deltas, "period": period}


@data_tools.tool
def compute_share(ctx: RunContext[DataAgent]) -> dict[str, Any] | str:
    """Add share_pct (percentage of total) to the last query result."""
    global _last_query_data
    if not _last_query_data or not _last_query_metric:
        return "No previous query. Run query_metric first."
    metric = _last_query_metric
    enriched = compute_shares(_last_query_data, metric)
    _last_query_data = enriched
    return {"ok": True, "data": enriched}


@data_tools.tool
def decompose_metric(
    ctx: RunContext[DataAgent],
    metric: str,
    period: str = "month",
    dimensions: list[str] | None = None,
) -> dict[str, Any] | str:
    """Explain why a metric changed. Compares current vs previous week/month/quarter.
    Pass dimensions only if user specified (e.g. ["region", "product_category"]).
    Omit to analyze all. Returns dimension_impacts and top_dimension_breakdown.
    Use contribution_pct: % of total change (negative = contributed to decline)."""
    result = decompose_metric_change(
        core=ctx.deps,
        metric=metric,
        period=period,
        dimensions=dimensions,
    )
    if not result.ok:
        return f"Decomposition failed: {result.error}"
    return {
        "ok": True,
        "metric": result.metric,
        "period": result.period,
        "total_delta": result.total_delta,
        "total_pct_change": result.total_pct_change,
        "dimension_impacts": result.dimension_impacts,
        "top_dimension": result.top_dimension,
        "top_dimension_breakdown": result.top_dimension_breakdown,
    }


@data_tools.tool
def export_to_csv(ctx: RunContext[DataAgent]) -> str:
    """Export the last query result to CSV."""
    global _last_query_data, _pending_files
    if not _last_query_data:
        return "No data to export. Run query_metric first."
    try:
        import csv
        export_dir = Path.cwd() / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = export_dir / f"export_{ts}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(_last_query_data[0].keys()))
            writer.writeheader()
            writer.writerows(_last_query_data)
        _pending_files.append({"path": str(path), "title": path.name})
        return f"Exported {len(_last_query_data)} rows to {path}"
    except Exception as e:
        return f"Export failed: {e}"


@data_tools.tool
def export_to_excel(ctx: RunContext[DataAgent]) -> str:
    """Export the last query result to Excel (.xlsx)."""
    global _last_query_data, _pending_files
    if not _last_query_data:
        return "No data to export. Run query_metric first."
    try:
        import pandas as pd
        export_dir = Path.cwd() / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = export_dir / f"export_{ts}.xlsx"
        df = pd.DataFrame(_last_query_data)
        df.to_excel(path, index=False)
        _pending_files.append({"path": str(path), "title": path.name})
        return f"Exported {len(_last_query_data)} rows to {path}"
    except ImportError:
        return "Excel export requires openpyxl. Install with: uv sync"
    except Exception as e:
        return f"Export failed: {e}"


@data_tools.tool
def export_to_google_sheets(ctx: RunContext[DataAgent]) -> str:
    """Export the last query result to Google Sheets. Requires GOOGLE_CREDENTIALS_JSON env."""
    global _last_query_data
    if not _last_query_data:
        return "No data to export. Run query_metric first."
    return "Google Sheets export requires additional setup. Use export_to_csv or export_to_excel for now."


@data_tools.tool
def generate_chart(
    ctx: RunContext[DataAgent],
    chart_type: str | None = None,
    dimension: str | None = None,
) -> str:
    """Generate a chart from the last query result. Auto-detects chart type if omitted.
    In Slack the chart is uploaded to the channel. In web UI, inline display is not supported — path is returned."""
    global _last_query_data, _last_query_metric, _pending_files
    if not _last_query_data or not _last_query_metric:
        return "No data to chart. Run query_metric first."
    metric = _last_query_metric
    group_by = [k for k in _last_query_data[0].keys() if k != metric]
    dim = dimension or (group_by[0] if group_by else None)
    if not dim:
        return "Need at least one dimension to chart."
    chart_type_actual = chart_type or suggest_chart_type(
        _last_query_data, dim, group_by, ctx.deps.bsl_models
    )
    if chart_type_actual == "line":
        msg, path = generate_line_chart(_last_query_data, metric, dim)
    elif chart_type_actual == "pie":
        msg, path = generate_pie_chart(_last_query_data, metric, dim)
    else:
        msg, path = generate_bar_chart(_last_query_data, metric, dim)
    if path:
        _pending_files.append({"path": str(path), "title": path.name})
        # Slack: chart is uploaded via _pending_files; return short message
        # Web UI: inline display not supported, return path
        if ctx.metadata and ctx.metadata.get("interface") == "slack":
            return f"Here's your chart: {metric} by {dim}."
        return f"Chart display not supported in web UI. Here is the path to the file: {path}"
    return msg


# ---------------------------------------------------------------------------
# Build agent
# ---------------------------------------------------------------------------

def _get_model() -> str:
    """Resolve LLM model from env or falk_project.yaml."""
    env_model = os.getenv("LLM_MODEL", "").strip()
    if env_model:
        if ":" not in env_model:
            return f"openai:{env_model}"
        return env_model
    from falk.settings import load_settings
    s = load_settings()
    provider = (s.agent.provider or "openai").lower()
    model = s.agent.model or "gpt-4o-mini"
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
        agent_config=agent_config,
        model_descriptions=core.model_descriptions,
        dimension_descriptions=core.dimension_descriptions,
        metric_synonyms=core.metric_synonyms,
        dimension_synonyms=core.dimension_synonyms,
        metric_gotchas=core.metric_gotchas,
        dimension_gotchas=core.dimension_gotchas,
        project_root=project_root,
    )
    toolsets: list = [data_tools]
    instructions: list = []
    if s.skills.enabled and s.skills.directories:
        try:
            from pydantic_ai_skills import SkillsToolset

            skill_dirs = [
                str((project_root / d).resolve()) if not Path(d).is_absolute() else d
                for d in s.skills.directories
            ]
            skills_toolset = SkillsToolset(directories=skill_dirs)
            toolsets.append(skills_toolset)

            async def add_skills_instructions(ctx: RunContext[DataAgent]) -> str | None:
                return await skills_toolset.get_instructions(ctx)

            instructions.append(add_skills_instructions)
        except ImportError:
            pass  # pydantic-ai-skills not installed
    agent = Agent(
        model=_get_model(),
        deps_type=DataAgent,
        toolsets=toolsets,
        system_prompt=system_prompt,
        instructions=instructions if instructions else None,
        output_type=str,
    )
    # Attach _pending_files for Slack uploads
    agent._pending_files = _pending_files  # type: ignore[attr-defined]
    return agent


def build_web_app():
    """Return ASGI app for local web UI (Agent.to_web)."""
    from starlette.staticfiles import StaticFiles

    agent = build_agent()
    app = agent.to_web(deps=DataAgent())

    # Mount charts dir (file paths returned when inline display not supported)
    charts_dir = Path.cwd() / "exports" / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/charts", StaticFiles(directory=str(charts_dir)), name="charts")

    return app

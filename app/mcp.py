"""MCP server for falk data agent using FastMCP.

Exposes falk's governed metric queries as MCP tools that any MCP client can use.
The server maintains a DataAgent instance and provides tools for querying metrics,
dimensions, and generating charts.

Usage:
    # Start with stdio transport (default for MCP)
    python -m app.mcp

    # Or via CLI
    falk mcp

    # Connect from Cursor, Claude Desktop, or other MCP clients
"""

from __future__ import annotations

import inspect
import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP

from falk.agent import DataAgent
from falk.llm import load_custom_toolsets, readiness_probe, tool_error
from falk.observability import configure_observability
from falk.services.query_service import execute_query_metric
from falk.settings import load_settings
from falk.tools.calculations import suggest_date_range as _suggest_date_range

# Load .env before initializing agent
_env_candidates = [Path(__file__).resolve().parent.parent / ".env", Path.cwd() / ".env"]
for _p in _env_candidates:
    if _p.exists():
        load_dotenv(_p, override=True)
        break
else:
    load_dotenv(override=True)

# Configure logging to stderr only (MCP uses stdout for JSON-RPC in stdio mode)
_settings = load_settings()
_log_level = str(_settings.advanced.log_level).upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Observability (Logfire tracing)
configure_observability()

# Initialize FastMCP server
mcp = FastMCP("falk")

# Initialize DataAgent (shared across all tool calls)
_agent: DataAgent | None = None

# Built-in MCP tool names (skip when registering extensions to avoid collisions)
_BUILTIN_MCP_TOOLS = frozenset(
    {
        "list_catalog",
        "suggest_date_range",
        "describe_metric",
        "describe_model",
        "describe_dimension",
        "lookup_dimension_values",
        "disambiguate",
        "query_metric",
        "health_check",
    }
)


def get_agent() -> DataAgent:
    """Get or create the shared DataAgent instance."""
    global _agent
    if _agent is None:
        logger.info("Initializing DataAgent from project configuration...")
        _agent = DataAgent()
        logger.info(f"DataAgent initialized with {len(_agent.bsl_models)} semantic models")
    return _agent


# ---------------------------------------------------------------------------
# MCP Tools - Discovery & Metadata
# ---------------------------------------------------------------------------


@mcp.tool()
def list_catalog(entity_type: str = "both") -> dict[str, Any]:
    """List metrics and/or dimensions.

    Args:
        entity_type: 'metric' | 'dimension' | 'both' (default: both)

    Returns {"metrics": [...], "dimensions": [...]} or subset.
    Use this to discover what metrics and dimensions are available before querying.
    """
    et = (entity_type or "both").strip().lower()
    if et not in ("metric", "dimension", "both"):
        return tool_error(
            f"entity_type must be 'metric', 'dimension', or 'both', got '{entity_type}'.",
            "INVALID_ENTITY_TYPE",
        )

    agent = get_agent()
    result: dict[str, Any] = {}
    if et in ("metric", "both"):
        result["metrics"] = agent.list_metrics().get("metrics", [])
    if et in ("dimension", "both"):
        result["dimensions"] = agent.list_dimensions().get("dimensions", [])
    return result


@mcp.tool()
def suggest_date_range(period: str) -> dict[str, Any]:
    """Get date range for common periods.

    Args:
        period: One of: yesterday, today, last_7_days, last_30_days, this_week,
                this_month, last_month, this_quarter.

    Returns {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} or {"error": "..."}.
    """
    try:
        return _suggest_date_range(period)
    except ValueError as e:
        return tool_error(str(e), "INVALID_DATE_PERIOD")


@mcp.tool()
def describe_metric(name: str) -> str:
    """Get full description of a metric including dimensions and time grains.

    Args:
        name: Metric name to describe

    Returns formatted description with available dimensions and time grains.
    """
    return get_agent().describe_metric(name)


@mcp.tool()
def describe_model(name: str) -> dict[str, Any] | str:
    """Get full description of a semantic model (metrics, dimensions, time grains).

    Args:
        name: Semantic model name to describe

    Returns dict with model details or error string if not found.
    """
    return get_agent().describe_model(name)


@mcp.tool()
def describe_dimension(name: str) -> str:
    """Get full description of a dimension (type, description, domain).

    Args:
        name: Dimension name to describe

    Returns formatted description with type, domain, and usage info.
    """
    return get_agent().describe_dimension(name)


@mcp.tool()
def lookup_dimension_values(
    dimension: str,
    limit: int = 100,
    search: str | None = None,
) -> dict[str, Any]:
    """Look up actual values for a dimension from the warehouse.

    Useful for finding valid filter values or autocomplete suggestions.

    Args:
        dimension: Dimension name to look up
        limit: Maximum number of values to return (default 100)
        search: Optional search string to filter values

    Returns dict with dimension name and list of values.
    """
    return get_agent().lookup_dimension_values(dimension, search, limit)


def _mcp_matches_concept(item: dict, concept: str) -> bool:
    """Case-insensitive substring match on name, display_name, or synonyms."""
    c = concept.lower().strip()
    if not c:
        return False
    name = (item.get("name") or "").lower()
    display = (item.get("display_name") or "").lower()
    if c in name or c in display:
        return True
    return any(c in str(syn).lower() for syn in item.get("synonyms") or [])


@mcp.tool()
def disambiguate(entity_type: str, concept: str) -> dict[str, Any]:
    """Find metrics or dimensions matching a concept (name or synonym).

    Use when the user's request is ambiguous — returns candidates so you can ask:
    'Which did you mean: A (description), B (description)?'

    Args:
        entity_type: 'metric' or 'dimension'
        concept: Search term (matched against name, display_name, synonyms)

    Returns dict with matches: [{name, display_name, description}, ...]
    """
    et = (entity_type or "").strip().lower()
    c = (concept or "").strip()
    if not c:
        return tool_error("Concept cannot be empty.", "INVALID_CONCEPT")
    if et not in ("metric", "dimension"):
        return tool_error(
            f"entity_type must be 'metric' or 'dimension', got '{entity_type}'.",
            "INVALID_ENTITY_TYPE",
        )

    get_agent()
    catalog = list_catalog(entity_type=et)
    items = catalog.get("metrics", []) if et == "metric" else catalog.get("dimensions", [])

    matches = [
        {
            "name": m.get("name"),
            "display_name": m.get("display_name") or m.get("name"),
            "description": (m.get("description") or "").strip() or None,
        }
        for m in items
        if _mcp_matches_concept(m, c)
    ]
    if not matches:
        return tool_error(f"No {et}s found for '{concept}'.", "NO_MATCHES")
    return {"matches": matches}


# ---------------------------------------------------------------------------
# MCP Tools - Querying
# ---------------------------------------------------------------------------


@mcp.tool()
def query_metric(
    metrics: list[str],
    dimensions: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    order_by: str | None = None,
    limit: int | None = None,
    time_grain: str | None = None,
    compare_period: str | None = None,
    include_share: bool = False,
) -> dict[str, Any]:
    """Query one or more metrics from the warehouse with optional grouping and filtering.

    This is the primary tool for retrieving metric data.

    Args:
        metrics: List of metric names to query (use list_catalog to discover)
        dimensions: Optional list of dimension names to group by
        filters: Optional list of filters, e.g.
            [{"field": "date", "op": ">=", "value": "2024-01-01"},
            {"field": "date", "op": "<=", "value": "2024-12-31"}]
        order_by: Optional ORDER BY direction ("asc" or "desc")
        limit: Optional row limit
        time_grain: Optional time grain (day, week, month, quarter, year)
        compare_period: Optional 'week'|'month'|'quarter' for period-over-period comparison
        include_share: If True, add share_pct column (percentage of total)

    Returns dict with:
        - rows: Query results as list of dicts
        - row_count: Number of rows returned
        - metrics: List of metric names
        - model: Semantic model name
    """
    result = execute_query_metric(
        core=get_agent(),
        metrics=metrics,
        dimensions=dimensions,
        filters=filters,
        order_by=order_by,
        limit=limit,
        time_grain=time_grain,
        compare_period=compare_period,
        include_share=include_share,
    )
    if not result.ok:
        return tool_error(
            result.error or "Query failed.",
            result.error_code or "QUERY_FAILED",
        )

    payload = {
        "rows": result.data,
        "row_count": result.rows,
        "metrics": result.metrics or metrics,
        "model": result.model,
    }
    if result.period:
        payload["period"] = result.period
    return payload


@mcp.tool()
def health_check() -> dict[str, Any]:
    """Return MCP runtime health status."""
    payload = readiness_probe(get_agent())
    payload["service"] = "mcp"
    return payload


# ---------------------------------------------------------------------------
# MCP Tools - Visualization
# ---------------------------------------------------------------------------
# NOTE: Chart generation has been migrated to BSL's built-in charting (in falk.llm).
# MCP charting tools are disabled as they require session state and BSL aggregates.
# Re-enable when MCP gains session state support or use llm agent directly.


# ---------------------------------------------------------------------------
# Custom tool extensions (from agent.extensions.tools)
# ---------------------------------------------------------------------------


def _make_mcp_ctx() -> SimpleNamespace:
    """Build minimal RunContext-like object for extension tools."""
    ctx = SimpleNamespace()
    ctx.deps = get_agent()
    ctx.metadata = {}
    return ctx


def _make_tool_wrapper(
    tool_name: str,
    tool_func: Any,
    tool_sig: inspect.Signature,
    tool_bound_params: list[inspect.Parameter],
    tool_description: str | None,
) -> Any:
    """Create MCP-compatible wrapper for a custom tool that takes RunContext."""
    def wrapper(**kwargs: Any) -> Any:
        ctx = _make_mcp_ctx()
        return tool_func(ctx, **kwargs)

    wrapper.__name__ = tool_name
    wrapper.__doc__ = tool_description or tool_func.__doc__
    wrapper.__signature__ = tool_sig.replace(  # type: ignore[attr-defined]
        parameters=tool_bound_params
    )
    return wrapper


def _register_custom_tools() -> None:
    """Load and register custom tool extensions from falk_project.yaml."""
    settings = load_settings()
    if not settings.agent.extensions_tools:
        return
    custom_toolsets = load_custom_toolsets(
        settings.project_root,
        settings.agent.extensions_tools,
    )
    for toolset in custom_toolsets:
        for name, tool in toolset.tools.items():
            if name in _BUILTIN_MCP_TOOLS:
                logger.warning("Custom tool '%s' shadows built-in; skipping", name)
                continue
            if not tool.takes_ctx:
                logger.warning(
                    "Custom tool '%s' does not take ctx; MCP requires RunContext, skipping",
                    name,
                )
                continue
            try:
                sig = inspect.signature(tool.function)
                params = list(sig.parameters.values())
                if not params or params[0].name not in ("ctx", "context"):
                    logger.warning(
                        "Custom tool '%s' has unexpected first param; skipping",
                        name,
                    )
                    continue
                bound_params = list(params[1:])
                wrapper = _make_tool_wrapper(
                    name,
                    tool.function,
                    sig,
                    bound_params,
                    getattr(tool, "description", None),
                )
                mcp.tool()(wrapper)
                logger.info("Registered custom MCP tool: %s", name)
            except Exception as e:
                logger.warning("Failed to register custom tool '%s': %s", name, e)


_register_custom_tools()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_server(
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Run the MCP server with stdio (default) or HTTP transport.

    Args:
        transport: 'stdio' for local Cursor/Claude, 'http' for shared server.
        host: Bind host for HTTP mode (ignored in stdio).
        port: Bind port for HTTP mode (ignored in stdio).
    """
    if transport == "http":
        logger.info("Starting falk MCP server (HTTP) at http://%s:%s/mcp", host, port)
        mcp.run(transport="http", host=host, port=port)
    else:
        logger.info("Starting falk MCP server (stdio)...")
        mcp.run(show_banner=False)


if __name__ == "__main__":
    run_server()

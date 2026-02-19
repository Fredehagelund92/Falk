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

import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP

from falk.agent import DataAgent
from falk.settings import load_settings
from falk.tools.calculations import compute_shares, period_date_ranges
from falk.tools.warehouse import run_warehouse_query

# Load .env before initializing agent
_env_candidates = [Path(__file__).resolve().parent.parent / ".env", Path.cwd() / ".env"]
for _p in _env_candidates:
    if _p.exists():
        load_dotenv(_p, override=True)
        break
else:
    load_dotenv(override=True)

# Configure logging from project settings
_settings = load_settings()
_log_level = str(_settings.advanced.log_level).upper()
logging.basicConfig(level=getattr(logging, _log_level, logging.INFO))
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("falk")

# Initialize DataAgent (shared across all tool calls)
_agent: DataAgent | None = None


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
def list_metrics() -> dict[str, Any]:
    """List all available metrics.
    
    Returns {"metrics": [{name, description, synonyms, gotcha}, ...]}.
    Use this to discover what metrics are available before querying.
    """
    return get_agent().list_metrics()


@mcp.tool()
def list_dimensions() -> dict[str, Any]:
    """List all available dimensions.
    
    Returns {"dimensions": [{name, display_name, description, synonyms, gotcha}, ...]}.
    Use display_name when showing dimensions to users.
    Dimensions can be used to group metrics in queries.
    """
    return get_agent().list_dimensions()


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
    for syn in (item.get("synonyms") or []):
        if c in str(syn).lower():
            return True
    return False


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
        return {"error": "Concept cannot be empty."}
    if et not in ("metric", "dimension"):
        return {"error": f"entity_type must be 'metric' or 'dimension', got '{entity_type}'."}

    agent = get_agent()
    if et == "metric":
        items = agent.list_metrics().get("metrics", [])
    else:
        items = agent.list_dimensions().get("dimensions", [])

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
        return {"error": f"No {et}s found for '{concept}'."}
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
) -> dict[str, Any]:
    """Query one or more metrics from the warehouse with optional grouping and filtering.
    
    This is the primary tool for retrieving metric data.
    
    Args:
        metrics: List of metric names to query (use list_metrics to discover)
        dimensions: Optional list of dimension names to group by
        filters: Optional list of filters, e.g. [{"field": "date", "op": ">=", "value": "2024-01-01"}, {"field": "date", "op": "<=", "value": "2024-12-31"}]
        order_by: Optional ORDER BY direction ("asc" or "desc")
        limit: Optional row limit
        time_grain: Optional time grain (day, week, month, quarter, year)
        
    Returns dict with:
        - rows: Query results as list of dicts
        - row_count: Number of rows returned
        - metrics: List of metric names
        - model: Semantic model name
    """
    agent = get_agent()
    
    result = run_warehouse_query(
        core=agent,
        metrics=metrics,
        dimensions=dimensions,
        filters=filters,
        order_by=order_by,
        limit=limit,
        time_grain=time_grain,
    )
    
    # Convert WarehouseQueryResult to dict
    if not result.ok:
        return {"error": result.error}
    
    return {
        "rows": result.data,
        "row_count": len(result.data),
        "metrics": result.metrics,
        "model": result.model,
    }


@mcp.tool()
def compare_periods(
    metric: str,
    dimension: str | None = None,
    period: str = "month",
    limit: int = 10,
) -> dict[str, Any]:
    """Compare a metric across time periods (e.g. this month vs last month).
    
    Automatically queries both current and previous period for comparison.
    
    Args:
        metric: Metric name to compare
        dimension: Optional dimension to group by
        period: Time period (day, week, month, quarter, year)
        limit: Maximum rows per period
        
    Returns dict with current_period, previous_period, and comparison data.
    """
    agent = get_agent()
    
    # Get date ranges for current and previous period
    current_range, previous_range = period_date_ranges(period)
    date_filters_cur = [
        {"field": "date", "op": ">=", "value": current_range[0]},
        {"field": "date", "op": "<=", "value": current_range[1]},
    ]
    date_filters_prev = [
        {"field": "date", "op": ">=", "value": previous_range[0]},
        {"field": "date", "op": "<=", "value": previous_range[1]},
    ]
    
    # Query both periods
    current_result = run_warehouse_query(
        core=agent,
        metrics=[metric],
        dimensions=[dimension] if dimension else [],
        filters=date_filters_cur,
        limit=limit,
    )
    
    previous_result = run_warehouse_query(
        core=agent,
        metrics=[metric],
        dimensions=[dimension] if dimension else [],
        filters=date_filters_prev,
        limit=limit,
    )
    
    return {
        "current_period": {
            "range": current_range,
            "rows": current_result.data,
            "row_count": len(current_result.data),
        },
        "previous_period": {
            "range": previous_range,
            "rows": previous_result.data,
            "row_count": len(previous_result.data),
        },
        "metric": metric,
        "dimension": dimension,
        "period": period,
    }


# ---------------------------------------------------------------------------
# MCP Tools - Visualization
# ---------------------------------------------------------------------------
# NOTE: Chart generation has been migrated to BSL's built-in charting (in llm.py).
# MCP charting tools are disabled as they require session state and BSL aggregates.
# Re-enable when MCP gains session state support or use llm agent directly.


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_server() -> None:
    """Run the MCP server with stdio transport (default)."""
    logger.info("Starting falk MCP server...")
    mcp.run()


if __name__ == "__main__":
    run_server()

"""MCP server for falk data agent using FastMCP.

Exposes falk's governed metric queries as MCP tools that any MCP client can use.
The server maintains a DataAgent instance and provides tools for:
- Listing and describing metrics/dimensions
- Querying metrics with filtering and grouping
- Metric decomposition (root cause analysis)
- Period comparisons
- Chart generation

Usage:
    # Start with stdio transport (default for MCP)
    python -m falk.mcp.server
    
    # Or via CLI
    falk mcp
    
    # Connect from Cursor, Claude Desktop, or other MCP clients
"""
from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP

from falk.agent import DataAgent
from falk.mcp import tools

# Configure logging
logging.basicConfig(level=logging.INFO)
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
    """List all available metrics grouped by semantic model.
    
    Returns dict with semantic_models containing model->metrics mapping.
    Use this to discover what metrics are available before querying.
    """
    agent = get_agent()
    return tools.list_metrics(agent)


@mcp.tool()
def list_dimensions() -> dict[str, Any]:
    """List all available dimensions across semantic models.
    
    Returns dict with dimensions containing list of dimension info.
    Dimensions can be used to group metrics in queries.
    """
    agent = get_agent()
    return tools.list_dimensions(agent)


@mcp.tool()
def describe_metric(name: str) -> str:
    """Get full description of a metric including dimensions and time grains.
    
    Args:
        name: Metric name to describe
        
    Returns formatted description with available dimensions and time grains.
    """
    agent = get_agent()
    return tools.describe_metric(agent, name)


@mcp.tool()
def describe_model(name: str) -> dict[str, Any] | str:
    """Get full description of a semantic model (metrics, dimensions, time grains).
    
    Args:
        name: Semantic model name to describe
        
    Returns dict with model details or error string if not found.
    """
    agent = get_agent()
    return tools.describe_model(agent, name)


@mcp.tool()
def describe_dimension(name: str) -> str:
    """Get full description of a dimension (type, description, domain).
    
    Args:
        name: Dimension name to describe
        
    Returns formatted description with type, domain, and usage info.
    """
    agent = get_agent()
    return tools.describe_dimension(agent, name)


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
    agent = get_agent()
    return tools.lookup_values(agent, dimension, limit, search)


# ---------------------------------------------------------------------------
# MCP Tools - Querying
# ---------------------------------------------------------------------------


@mcp.tool()
def query_metric(
    metric: str,
    dimensions: list[str] | None = None,
    where: str | None = None,
    order_by: str | None = None,
    limit: int | None = None,
    time_grain: str | None = None,
) -> dict[str, Any]:
    """Query a metric from the warehouse with optional grouping and filtering.
    
    This is the primary tool for retrieving metric data.
    
    Args:
        metric: Metric name to query (use list_metrics to discover)
        dimensions: Optional list of dimension names to group by
        where: Optional WHERE clause for filtering
               Supported formats:
               - Simple: "region = 'US'"
               - Comparison: "date >= '2024-01-01'"
               - Combined: "region = 'US' AND date >= '2024-01-01'"
               - IN clause: "region IN ('US', 'EU')"
        order_by: Optional ORDER BY clause (e.g. "revenue DESC")
        limit: Optional row limit
        time_grain: Optional time grain (day, week, month, quarter, year)
        
    Returns dict with:
        - rows: Query results as list of dicts
        - row_count: Number of rows returned
        - metric: Metric name
        - model: Semantic model name
    """
    agent = get_agent()
    return tools.query_metric(
        agent=agent,
        metric=metric,
        dimensions=dimensions,
        where=where,
        order_by=order_by,
        limit=limit,
        time_grain=time_grain,
    )


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
    return tools.compare_periods(agent, metric, dimension, period, limit)


@mcp.tool()
def decompose_metric(
    metric: str,
    dimension: str | None = None,
    period: str = "month",
) -> dict[str, Any]:
    """Decompose a metric change to find root causes (variance analysis).
    
    This performs automatic root cause analysis by:
    1. Comparing current vs previous period
    2. Breaking down by top dimensions
    3. Computing variance contribution
    
    Use this to answer "why did X change?" questions.
    
    Args:
        metric: Metric name to decompose
        dimension: Optional specific dimension to analyze (if None, analyzes all)
        period: Time period for comparison (day, week, month, quarter, year)
        
    Returns dict with decomposition results and variance drivers.
    """
    agent = get_agent()
    return tools.decompose_metric(agent, metric, dimension, period)


# ---------------------------------------------------------------------------
# MCP Tools - Visualization
# ---------------------------------------------------------------------------


@mcp.tool()
def generate_chart(
    chart_type: str,
    data: dict[str, Any],
    title: str | None = None,
) -> dict[str, Any]:
    """Generate a chart (bar, line, pie) from query data.
    
    Args:
        chart_type: Chart type (bar, line, pie)
        data: Query result from query_metric (must have rows key)
        title: Optional chart title
        
    Returns dict with chart data in Plotly format.
    """
    agent = get_agent()
    return tools.generate_chart(agent, chart_type, data, title)


@mcp.tool()
def suggest_chart(data: dict[str, Any]) -> str:
    """Suggest best chart type for query data.
    
    Analyzes the structure of query results to recommend bar, line, or pie chart.
    
    Args:
        data: Query result from query_metric
        
    Returns suggested chart type as string.
    """
    agent = get_agent()
    return tools.suggest_chart(agent, data)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_server() -> None:
    """Run the MCP server with stdio transport (default)."""
    logger.info("Starting falk MCP server...")
    mcp.run()


if __name__ == "__main__":
    run_server()

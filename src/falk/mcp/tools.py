"""MCP tools for falk data agent.

All tools operate on a shared DataAgent instance provided by the MCP server.
These tools expose governed metric queries to any MCP client.
"""
from __future__ import annotations

from typing import Any

from falk.agent import DataAgent
from falk.tools.calculations import compute_shares, period_date_ranges
from falk.tools.charts import (
    generate_bar_chart,
    generate_line_chart,
    generate_pie_chart,
    suggest_chart_type,
)
from falk.tools.semantic import get_semantic_model_info
from falk.tools.warehouse import (
    decompose_metric_change,
    lookup_dimension_values,
    run_warehouse_query,
)
from falk.tools.where_parser import parse_where_clause


# ---------------------------------------------------------------------------
# Tool Functions (called by MCP server with agent context)
# ---------------------------------------------------------------------------


def list_metrics(agent: DataAgent) -> dict[str, Any]:
    """List all available metrics grouped by semantic model.
    
    Returns:
        Dictionary with semantic_models key containing model->metrics mapping
    """
    return agent.list_metrics()


def list_dimensions(agent: DataAgent) -> dict[str, Any]:
    """List all available dimensions across semantic models.
    
    Returns:
        Dictionary with dimensions key containing list of dimension info
    """
    all_dims: list[dict[str, Any]] = []
    for model_name, model in agent.bsl_models.items():
        for dim_name, dim in model.get_dimensions().items():
            display_name = agent.dimension_display_names.get((model_name, dim_name), "") or dim_name
            desc = agent.dimension_descriptions.get((model_name, dim_name), "") or ""
            dom = agent.dimension_domains.get((model_name, dim_name), "") or ""
            all_dims.append({
                "name": dim_name,
                "display_name": display_name,
                "description": desc,
                "domain": dom,
            })
    return {"dimensions": all_dims}


def describe_metric(agent: DataAgent, name: str) -> str:
    """Get full description of a metric including dimensions and time grains.
    
    Args:
        name: Metric name to describe
        
    Returns:
        Formatted description string
    """
    info = get_semantic_model_info(
        agent.bsl_models,
        name,
        agent.model_descriptions,
    )
    if not info:
        return f"Metric '{name}' not found. Use list_metrics to see available metrics."
    
    dim_str = ", ".join(d.name for d in info.dimensions) if info.dimensions else "none"
    grains_str = ", ".join(info.time_grains) if info.time_grains else "none"
    return f"**{name}** — {info.description}. Dimensions: {dim_str}. Time grains: {grains_str}."


def describe_model(agent: DataAgent, name: str) -> dict[str, Any] | str:
    """Get full description of a semantic model (metrics, dimensions, time grains).
    
    Args:
        name: Model name to describe
        
    Returns:
        Dictionary with model details or error string
    """
    info = get_semantic_model_info(
        agent.bsl_models,
        name,
        agent.model_descriptions,
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


def describe_dimension(agent: DataAgent, name: str) -> str:
    """Get full description of a dimension (type, description, domain).
    
    Args:
        name: Dimension name to describe
        
    Returns:
        Formatted description string
    """
    found: dict[str, Any] | None = None
    for model_name, model in agent.bsl_models.items():
        for dim_name, dim in model.get_dimensions().items():
            if dim_name == name:
                display_name = agent.dimension_display_names.get((model_name, dim_name), "") or dim_name
                desc = agent.dimension_descriptions.get((model_name, dim_name), "") or ""
                dom = agent.dimension_domains.get((model_name, dim_name), "") or ""
                found = {
                    "name": dim_name,
                    "display_name": display_name,
                    "description": desc,
                    "domain": dom,
                }
                break
        if found:
            break
    
    if not found:
        return f"Dimension '{name}' not found. Use list_dimensions to see available dimensions."
    
    # Show technical name in parentheses only if display_name is different
    display_name = found['display_name']
    tech_name = found['name']
    if display_name != tech_name:
        lead = f"**{display_name}** (`{tech_name}`)"
    else:
        lead = f"**{display_name}**"
    
    if found["description"]:
        lead += f" — {found['description']}"
    if found["domain"]:
        lead += f". Domain: {found['domain']}"
    return lead


def lookup_values(
    agent: DataAgent,
    dimension: str,
    limit: int = 100,
    search: str | None = None,
) -> dict[str, Any]:
    """Look up actual values for a dimension from the warehouse.
    
    Args:
        dimension: Dimension name to look up
        limit: Maximum number of values to return (default 100)
        search: Optional search string to filter values
        
    Returns:
        Dictionary with dimension and values keys
    """
    values = lookup_dimension_values(agent.bsl_models, dimension, search)
    return {
        "dimension": dimension,
        "values": values or []
    }


def query_metric(
    agent: DataAgent,
    metric: str,
    dimensions: list[str] | None = None,
    where: str | None = None,
    order_by: str | None = None,
    limit: int | None = None,
    time_grain: str | None = None,
) -> dict[str, Any]:
    """Query a metric from the warehouse with optional grouping and filtering.
    
    Args:
        metric: Metric name to query
        dimensions: Optional list of dimensions to group by
        where: Optional WHERE clause for filtering
        order_by: Optional ORDER BY clause
        limit: Optional row limit
        time_grain: Optional time grain (day, week, month, quarter, year)
        
    Returns:
        Dictionary with sql, rows, and row_count keys
    """
    # Parse WHERE clause string into BSL filters
    filters = None
    if where:
        filters = parse_where_clause(where)
        if filters is None:
            return {"error": f"Failed to parse WHERE clause: {where}"}
    
    result = run_warehouse_query(
        core=agent,
        metric=metric,
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
        "metric": result.metric,
        "model": result.model,
    }


def compare_periods(
    agent: DataAgent,
    metric: str,
    dimension: str | None = None,
    period: str = "month",
    limit: int = 10,
) -> dict[str, Any]:
    """Compare a metric across time periods (e.g. this month vs last month).
    
    Args:
        metric: Metric name to compare
        dimension: Optional dimension to group by
        period: Time period (day, week, month, quarter, year)
        limit: Maximum rows per period
        
    Returns:
        Dictionary with current, previous, and comparison data
    """
    # Get date ranges for current and previous period
    current_range, previous_range = period_date_ranges(period)
    
    # Query both periods
    current_result = run_warehouse_query(
        core=agent,
        metric=metric,
        dimensions=[dimension] if dimension else [],
        filters={"date": {"gte": current_range[0], "lte": current_range[1]}},
        limit=limit,
    )
    
    previous_result = run_warehouse_query(
        core=agent,
        metric=metric,
        dimensions=[dimension] if dimension else [],
        filters={"date": {"gte": previous_range[0], "lte": previous_range[1]}},
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


def decompose_metric(
    agent: DataAgent,
    metric: str,
    dimension: str | None = None,
    period: str = "month",
) -> dict[str, Any]:
    """Decompose a metric change to find root causes (variance analysis).
    
    This performs automatic root cause analysis by:
    1. Comparing current vs previous period
    2. Breaking down by top dimensions
    3. Computing variance contribution
    
    Args:
        metric: Metric name to decompose
        dimension: Optional dimension to analyze (if None, analyzes all)
        period: Time period for comparison
        
    Returns:
        Dictionary with decomposition results
    """
    result = decompose_metric_change(
        core=agent,
        metric=metric,
        period=period,
        dimensions=[dimension] if dimension else None,
    )
    
    # Convert MetricDecompositionResult to dict
    return {
        "metric": result.metric,
        "current_value": result.current_value,
        "previous_value": result.previous_value,
        "change": result.change,
        "change_pct": result.change_pct,
        "top_dimension": result.top_dimension,
        "variance_explained": result.variance_explained,
        "breakdown": [
            {
                "dimension_value": item.dimension_value,
                "current": item.current,
                "previous": item.previous,
                "change": item.change,
                "change_pct": item.change_pct,
                "contribution": item.contribution,
            }
            for item in result.breakdown
        ],
    }


def generate_chart(
    agent: DataAgent,
    chart_type: str,
    data: dict[str, Any],
    title: str | None = None,
) -> dict[str, Any]:
    """Generate a chart (bar, line, pie) from query data.
    
    Args:
        chart_type: Chart type (bar, line, pie)
        data: Query result data with rows
        title: Optional chart title
        
    Returns:
        Dictionary with chart data and metadata
    """
    rows = data.get("rows", [])
    if not rows:
        return {"error": "No data to chart"}
    
    if chart_type == "bar":
        return generate_bar_chart(rows, title)
    elif chart_type == "line":
        return generate_line_chart(rows, title)
    elif chart_type == "pie":
        return generate_pie_chart(rows, title)
    else:
        return {"error": f"Unknown chart type: {chart_type}"}


def suggest_chart(
    agent: DataAgent,
    data: dict[str, Any],
) -> str:
    """Suggest best chart type for query data.
    
    Args:
        data: Query result data with rows
        
    Returns:
        Suggested chart type (bar, line, pie)
    """
    rows = data.get("rows", [])
    return suggest_chart_type(rows)

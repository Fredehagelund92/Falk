"""Warehouse query execution using the Boring Semantic Layer (BSL).

This module provides warehouse interaction tools:
- ``run_warehouse_query`` — Execute semantic queries via BSL
- ``lookup_dimension_values`` — Get distinct values for a dimension (with optional search)
- ``decompose_metric_change`` — Explain why metrics changed (automatic root cause analysis)

BSL handles all SQL generation, type casting, and execution.  Compared with
the previous hand-built-SQL approach this eliminates:

- SQL-injection risks (no string interpolation)
- DATE vs VARCHAR casting bugs (BSL auto-casts filter values)
- Manual aggregation logic (BSL resolves ``SUM(col)`` from measure defs)

The ``WarehouseQueryResult`` dataclass is unchanged so the rest of the
codebase (``pydantic_agent.py``, ``calculations.py``, exports) doesn't
need to care that BSL is the engine underneath.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from falk.tools.calculations import (
    compute_deltas,
    calculate_variance_explained,
    period_date_ranges,
)

# ---------------------------------------------------------------------------
# Time-grain mapping: agent-friendly names → BSL constants
# ---------------------------------------------------------------------------

_TIME_GRAIN_MAP: dict[str, str] = {
    "day": "TIME_GRAIN_DAY",
    "week": "TIME_GRAIN_WEEK",
    "month": "TIME_GRAIN_MONTH",
    "quarter": "TIME_GRAIN_QUARTER",
    "year": "TIME_GRAIN_YEAR",
}


# ---------------------------------------------------------------------------
# Result dataclass (unchanged from the old implementation)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WarehouseQueryResult:
    """Result of a warehouse query."""
    ok: bool
    data: list[dict[str, Any]]
    error: str | None = None
    model: str | None = None
    metric: str | None = None


# ---------------------------------------------------------------------------
# Main query function
# ---------------------------------------------------------------------------

def run_warehouse_query(
    core: Any = None,
    bsl_models: dict[str, Any] | None = None,
    query_object: dict[str, Any] | None = None,
    metric: str | None = None,
    dimensions: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    time_grain: str | None = None,
    limit: int | None = None,
    order_by: Any = None,
) -> WarehouseQueryResult:
    """Execute a warehouse query using BSL semantic models.

    Supports two call styles:

    1. Agent style (core + named args)::
        run_warehouse_query(core=core, metric="clicks", dimensions=["platform"], ...)

    2. CLI/quality style (bsl_models + query_object)::
        run_warehouse_query(bsl_models=core.bsl_models, query_object={"metric": "clicks", ...})

    Args:
        core:       DataAgent instance (provides BSL models). Use with metric, dimensions, etc.
        bsl_models: BSL models dict (alternative to core). Use with query_object.
        query_object: Query spec dict with metric, dimensions, filters, time_grain, limit.
        metric:     Metric name (e.g., ``"clicks"``).
        dimensions: List of dimension names (e.g., ``["platform", "country"]``).
        filters:    Dict of filters (e.g., ``{"country": "US", "date": {"gte": "2024-01-01"}}``).
        time_grain: Optional time grain (``"day"``, ``"week"``, ``"month"``, ``"quarter"``, ``"year"``).
        limit:      Max rows to return.
        order_by:   Sort direction (``"asc"`` or ``"desc"``).

    Returns:
        WarehouseQueryResult with ``ok=True`` and ``data`` on success,
        or ``ok=False`` and ``error`` on failure.
    """
    # Resolve models and query params from either call style
    models = (core.bsl_models if core is not None else bsl_models) or {}
    if query_object:
        metric = query_object.get("metric") or metric
        dimensions = query_object.get("dimensions") or dimensions
        filters = filters or _query_filters_to_dict(query_object.get("filters"))
        time_grain = query_object.get("time_grain") or time_grain
        limit = query_object.get("limit") or limit
        order_by = query_object.get("order_by") or query_object.get("order") or order_by

    if not metric or not models:
        return WarehouseQueryResult(
            ok=False,
            data=[],
            error="metric and bsl_models/core required",
        )

    try:
        # 1) Find which semantic model contains this metric (BSL uses get_measures)
        model_name = None
        model = None
        for name, m in models.items():
            measures = m.get_measures() if hasattr(m, "get_measures") else (m.get("measures") or {})
            if metric in measures:
                model_name = name
                model = m
                break

        if model is None or not model_name:
            return WarehouseQueryResult(
                ok=False,
                data=[],
                error=f"Metric '{metric}' not found in any semantic model.",
            )

        # 2) Build BSL query params
        bsl_filters = _convert_filters_to_bsl(filters) if filters else None
        bsl_order = _parse_order_by(order_by, metric) if order_by else None
        bsl_grain = _TIME_GRAIN_MAP.get((time_grain or "").lower()) if time_grain else None

        # 3) Execute via model.query() (BSL SemanticTable API)
        query_result = model.query(
            dimensions=dimensions or [],
            measures=[metric],
            filters=bsl_filters,
            order_by=bsl_order,
            limit=limit,
            time_grain=bsl_grain,
        )
        result_df = query_result.execute()

        # 4) Convert DataFrame → list of dicts
        data = result_df.to_dict(orient="records") if result_df is not None else []

        return WarehouseQueryResult(
            ok=True,
            data=data,
            model=model_name,
            metric=metric,
        )

    except Exception as e:
        return WarehouseQueryResult(
            ok=False,
            data=[],
            error=str(e),
        )


def _query_filters_to_dict(
    filters: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Convert agent-style filter list to dict for _convert_filters_to_bsl.

    Agent filters: [{"dimension": "country", "op": "=", "value": "US"}, ...]
    """
    if not filters:
        return None
    out: dict[str, Any] = {}
    for f in filters:
        if not isinstance(f, dict):
            continue
        dim = f.get("dimension") or f.get("field")
        op = (f.get("op") or f.get("operator", "=")).strip().upper()
        val = f.get("value")
        if dim is None or val is None:
            continue
        if op == "IN" and isinstance(val, list):
            out[dim] = val
        elif op in ("=", "EQ", "EQUALS"):
            out[dim] = val
        elif op in (">=", "GTE"):
            out[dim] = {"gte": val} if dim not in out else {**out[dim], "gte": val}
        elif op in ("<=", "LTE"):
            out[dim] = {"lte": val} if dim not in out else {**out[dim], "lte": val}
        elif op in (">", "GT"):
            out[dim] = {"gt": val} if dim not in out else {**out[dim], "gt": val}
        elif op in ("<", "LT"):
            out[dim] = {"lt": val} if dim not in out else {**out[dim], "lt": val}
        else:
            out[dim] = val
    return out if out else None


# ---------------------------------------------------------------------------
# Dimension value lookup
# ---------------------------------------------------------------------------


def lookup_dimension_values(
    bsl_models: dict[str, Any],
    dimension: str,
    search: str | None = None,
) -> list[str] | None:
    """Look up distinct values for a dimension in the warehouse.

    Use this before filtering to find exact warehouse values for a dimension
    (e.g., partner names, countries, regions).

    Args:
        bsl_models: BSL SemanticModel objects keyed by model name.
        dimension: Dimension name (e.g., "partner", "country").
        search: Optional search term (case-insensitive partial match).

    Returns:
        List of matching values, or None if the dimension is not found in any model.
    """
    # 1) Find which semantic model contains this dimension
    model_name = None
    model = None
    for name, m in bsl_models.items():
        dims = m.get_dimensions() if hasattr(m, "get_dimensions") else (m.get("dimensions") or {})
        if dimension in dims:
            model_name = name
            model = m
            break

    if model is None or not model_name:
        return None

    # 2) Get a measure to run the query (we need at least one for BSL)
    measures = model.get_measures() if hasattr(model, "get_measures") else model.get("measures", {})
    if not measures:
        return None
    first_measure = next(iter(measures.keys()))

    # 3) Execute query to get distinct dimension values
    try:
        query_result = model.query(
            dimensions=[dimension],
            measures=[first_measure],
            limit=10000,
        )
        df = query_result.execute()
    except Exception:
        return None

    if df is None or df.empty:
        return []

    # 4) Extract unique values from the dimension column
    if dimension not in df.columns:
        return []

    values = df[dimension].dropna().astype(str).unique().tolist()
    values = sorted(set(v.strip() for v in values if v and str(v).strip()))

    # 5) Filter by search if provided
    if search and search.strip():
        search_lower = search.strip().lower()
        values = [v for v in values if search_lower in str(v).lower()]

    return values


# ---------------------------------------------------------------------------
# Filter conversion helpers
# ---------------------------------------------------------------------------

# BSL expects ">=", "<=", ">", "<" — not "gte", "lte", etc.
_BSL_OP_MAP: dict[str, str] = {
    "gte": ">=",
    "ge": ">=",
    "lte": "<=",
    "le": "<=",
    "gt": ">",
    "lt": "<",
}


def _convert_filters_to_bsl(filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert agent-style filters to BSL where clauses.

    Agent style:
        {"country": "US", "date": {"gte": "2024-01-01", "lte": "2024-12-31"}}

    BSL style:
        [
            {"field": "country", "operator": "equals", "value": "US"},
            {"field": "date", "operator": ">=", "value": "2024-01-01"},
            {"field": "date", "operator": "<=", "value": "2024-12-31"},
        ]
    """
    bsl_filters: list[dict[str, Any]] = []

    for field, value in filters.items():
        if isinstance(value, dict):
            # Range filter (e.g., {"gte": "2024-01-01", "lte": "2024-12-31"})
            for op, val in value.items():
                bsl_op = _BSL_OP_MAP.get(op, op)
                bsl_filters.append({
                    "field": field,
                    "operator": bsl_op,
                    "value": val,
                })
        elif isinstance(value, list):
            # IN filter (e.g., ["US", "CA"]) — BSL uses "values" not "value"
            bsl_filters.append({
                "field": field,
                "operator": "in",
                "values": value,
            })
        else:
            # Equality filter (e.g., "US")
            bsl_filters.append({
                "field": field,
                "operator": "equals",
                "value": value,
            })

    return bsl_filters


def _parse_order_by(
    order_by: Any,
    metric: str,
) -> list[tuple[str, str]] | None:
    """Convert agent order_by → BSL order_by.

    Agent: ``"desc"``  (sorts by the metric column)
    BSL:   ``[("clicks", "desc")]``
    """
    if not isinstance(order_by, str):
        return None
    direction = order_by.strip().lower()
    if direction in ("asc", "desc"):
        return [(metric, direction)]
    return None


# ---------------------------------------------------------------------------
# Metric decomposition (root cause analysis)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MetricDecompositionResult:
    """Result of decomposing a metric change."""
    ok: bool
    metric: str
    period: str
    total_delta: float
    total_pct_change: float | None
    current_value: float
    previous_value: float
    dimension_impacts: list[dict[str, Any]]  # Ranked dimensions by impact
    top_dimension: str | None
    top_dimension_breakdown: list[dict[str, Any]]  # Detailed breakdown of top dimension
    error: str | None = None


def decompose_metric_change(
    core,  # DataAgentCore instance
    metric: str,
    period: str = "month",
    dimensions: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    max_breakdown_items: int = 10,
    min_impact_threshold: float = 0.05,
) -> MetricDecompositionResult:
    """Decompose a metric change to explain what drove it.
    
    This is falk's killer feature for root cause analysis. It:
    1. Compares metric: current vs previous period
    2. Ranks all dimensions by impact (which explains the most variance?)
    3. Drills into the top dimension to show specific contributors
    4. Returns a structured breakdown for the agent to present
    
    Args:
        core: DataAgentCore instance (for BSL models and connection)
        metric: Metric name (e.g., "revenue", "orders")
        period: "week", "month", or "quarter" (default: "month")
        dimensions: List of dimensions to analyze (default: all available)
        filters: Optional filters to apply (e.g., {"region": "North America"})
        max_breakdown_items: Max items to show in top dimension breakdown
        min_impact_threshold: Only show dimension values with >5% impact
    
    Returns:
        MetricDecompositionResult with ranked dimensions and detailed breakdown
    
    Example:
        >>> result = decompose_metric_change(core, "revenue", period="month")
        >>> print(f"Revenue changed by {result.total_pct_change}%")
        >>> print(f"Top driver: {result.top_dimension} (explains {result.dimension_impacts[0]['variance_explained_pct']}%)")
        >>> for item in result.top_dimension_breakdown[:3]:
        ...     print(f"  - {item['dimension_value']}: {item['variance_pct']}% of change")
    """
    try:
        # Get date ranges for current vs previous period
        (cur_start, cur_end), (prev_start, prev_end) = period_date_ranges(period)
        
        # Get available dimensions if not specified
        if dimensions is None:
            # Get all dimensions from the metric's semantic model
            model_name = None
            for name, model in core.bsl_models.items():
                measures = model.get_measures() if hasattr(model, "get_measures") else (model.get("measures") or {})
                if metric in measures:
                    model_name = name
                    break
            
            if not model_name:
                return MetricDecompositionResult(
                    ok=False,
                    metric=metric,
                    period=period,
                    total_delta=0.0,
                    total_pct_change=None,
                    current_value=0.0,
                    previous_value=0.0,
                    dimension_impacts=[],
                    top_dimension=None,
                    top_dimension_breakdown=[],
                    error=f"Metric '{metric}' not found in any semantic model",
                )
            
            # Get dimensions from the model; exclude time dimensions (date, etc.)
            # Time dimensions are meaningless for period-over-period decomposition—
            # we're already comparing current vs previous week/month.
            m = core.bsl_models[model_name]
            dims_obj = m.get_dimensions() if hasattr(m, "get_dimensions") else (m.get("dimensions") or {})
            dimensions = [
                k for k in dims_obj.keys()
                if not getattr(dims_obj.get(k), "is_time_dimension", False)
            ]
        
        if not dimensions:
            return MetricDecompositionResult(
                ok=False,
                metric=metric,
                period=period,
                total_delta=0.0,
                total_pct_change=None,
                current_value=0.0,
                previous_value=0.0,
                dimension_impacts=[],
                top_dimension=None,
                top_dimension_breakdown=[],
                error="No dimensions available for decomposition",
            )
        
        # Query 1: Get total metric for current period
        current_filters = {**(filters or {}), "date": {"gte": cur_start, "lte": cur_end}}
        current_total_result = run_warehouse_query(
            core=core,
            metric=metric,
            dimensions=[],
            filters=current_filters,
        )
        
        if not current_total_result.ok or not current_total_result.data:
            return MetricDecompositionResult(
                ok=False,
                metric=metric,
                period=period,
                total_delta=0.0,
                total_pct_change=None,
                current_value=0.0,
                previous_value=0.0,
                dimension_impacts=[],
                top_dimension=None,
                top_dimension_breakdown=[],
                error=f"Failed to query current period: {current_total_result.error}",
            )
        
        # Query 2: Get total metric for previous period
        previous_filters = {**(filters or {}), "date": {"gte": prev_start, "lte": prev_end}}
        previous_total_result = run_warehouse_query(
            core=core,
            metric=metric,
            dimensions=[],
            filters=previous_filters,
        )
        
        if not previous_total_result.ok or not previous_total_result.data:
            return MetricDecompositionResult(
                ok=False,
                metric=metric,
                period=period,
                total_delta=0.0,
                total_pct_change=None,
                current_value=0.0,
                previous_value=0.0,
                dimension_impacts=[],
                top_dimension=None,
                top_dimension_breakdown=[],
                error=f"Failed to query previous period: {previous_total_result.error}",
            )
        
        # Calculate total change
        current_value = float(current_total_result.data[0].get(metric, 0))
        previous_value = float(previous_total_result.data[0].get(metric, 0))
        total_delta = current_value - previous_value
        total_pct_change = (
            round((total_delta / previous_value) * 100, 1) 
            if previous_value != 0 else None
        )
        
        # If no change, return early
        if abs(total_delta) < 0.01:
            return MetricDecompositionResult(
                ok=True,
                metric=metric,
                period=period,
                total_delta=0.0,
                total_pct_change=0.0,
                current_value=current_value,
                previous_value=previous_value,
                dimension_impacts=[],
                top_dimension=None,
                top_dimension_breakdown=[],
            )
        
        # Query 3: Get metric by each dimension for current period
        current_by_dims = {}
        previous_by_dims = {}
        
        for dim in dimensions:
            # Current period by dimension
            cur_result = run_warehouse_query(
                core=core,
                metric=metric,
                dimensions=[dim],
                filters=current_filters,
            )
            if cur_result.ok and cur_result.data:
                current_by_dims[dim] = cur_result.data
            
            # Previous period by dimension
            prev_result = run_warehouse_query(
                core=core,
                metric=metric,
                dimensions=[dim],
                filters=previous_filters,
            )
            if prev_result.ok and prev_result.data:
                previous_by_dims[dim] = prev_result.data
        
        # Rank dimensions by impact
        dimension_impacts = []
        for dim in dimensions:
            if dim not in current_by_dims or dim not in previous_by_dims:
                continue
            
            # Compute deltas for this dimension
            deltas = compute_deltas(
                current=current_by_dims[dim],
                previous=previous_by_dims[dim],
                metric=metric,
                group_keys=[dim],
            )
            
            # Calculate variance explained
            enriched = calculate_variance_explained(
                total_delta=total_delta,
                dimension_deltas=deltas,
                metric_key="delta",
            )
            
            # Impact = largest single contributor in this dimension as % of total change.
            # E.g. "Electronics alone explains 38% of the decline" — interpretable, capped at 100%.
            max_abs_delta = max((abs(d.get("delta", 0)) for d in enriched), default=0.0)
            primary_pct = (max_abs_delta / abs(total_delta)) * 100 if total_delta != 0 else 0.0
            
            dimension_impacts.append({
                "dimension": dim,
                "variance_explained_pct": round(min(primary_pct, 100.0), 1),
                "impact_score": round(min(primary_pct, 100.0), 1),
            })
        
        # Sort by impact
        dimension_impacts.sort(key=lambda x: x["impact_score"], reverse=True)
        
        # Get detailed breakdown for top dimension
        top_dimension = dimension_impacts[0]["dimension"] if dimension_impacts else None
        top_dimension_breakdown = []
        
        if top_dimension:
            deltas = compute_deltas(
                current=current_by_dims[top_dimension],
                previous=previous_by_dims[top_dimension],
                metric=metric,
                group_keys=[top_dimension],
            )
            
            enriched = calculate_variance_explained(
                total_delta=total_delta,
                dimension_deltas=deltas,
                metric_key="delta",
            )
            
            # Filter by impact threshold and limit. contribution_pct = delta/total_delta*100
            # (signed: negative = contributed to decline, positive = contributed to growth)
            significant = [
                {
                    "dimension_value": d.get(top_dimension),
                    "current": round(d.get("current", 0), 2),
                    "previous": round(d.get("previous", 0), 2),
                    "delta": round(d.get("delta", 0), 2),
                    "pct_change": d.get("pct_change"),
                    "contribution_pct": round(d.get("variance_pct", 0), 1),  # % of total change
                    "impact_rank": d.get("impact_rank"),
                }
                for d in enriched
                if abs(d.get("variance_pct", 0)) >= (min_impact_threshold * 100)
            ]
            
            top_dimension_breakdown = significant[:max_breakdown_items]
        
        return MetricDecompositionResult(
            ok=True,
            metric=metric,
            period=period,
            total_delta=round(total_delta, 2),
            total_pct_change=total_pct_change,
            current_value=round(current_value, 2),
            previous_value=round(previous_value, 2),
            dimension_impacts=dimension_impacts,
            top_dimension=top_dimension,
            top_dimension_breakdown=top_dimension_breakdown,
        )
    
    except Exception as e:
        return MetricDecompositionResult(
            ok=False,
            metric=metric,
            period=period,
            total_delta=0.0,
            total_pct_change=None,
            current_value=0.0,
            previous_value=0.0,
            dimension_impacts=[],
            top_dimension=None,
            top_dimension_breakdown=[],
            error=str(e),
        )

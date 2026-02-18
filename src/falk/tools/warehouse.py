"""Warehouse query execution using the Boring Semantic Layer (BSL).

This module provides warehouse interaction tools:
- ``run_warehouse_query`` — Execute semantic queries via BSL
- ``lookup_dimension_values`` — Get distinct values for a dimension (with optional search)

BSL handles all SQL generation, type casting, and execution.  Compared with
the previous hand-built-SQL approach this eliminates:

- SQL-injection risks (no string interpolation)
- DATE vs VARCHAR casting bugs (BSL auto-casts filter values)
- Manual aggregation logic (BSL resolves ``SUM(col)`` from measure defs)

The ``WarehouseQueryResult`` dataclass exposes ``metrics`` (list) so
downstream code can use the same BSL engine regardless of single vs multiple measures.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any


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
    metrics: list[str] = ()  # One or more measure names (when ok=True)
    aggregate: Any = None  # BSL SemanticAggregate for charting (when ok=True)


# ---------------------------------------------------------------------------
# Main query function
# ---------------------------------------------------------------------------

def run_warehouse_query(
    core: Any = None,
    bsl_models: dict[str, Any] | None = None,
    metrics: list[str] | None = None,
    dimensions: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    time_grain: str | None = None,
    limit: int | None = None,
    order_by: Any = None,
) -> WarehouseQueryResult:
    """Execute a warehouse query using BSL semantic models.

    Call with core (or bsl_models) and named args::
        run_warehouse_query(core=core, metrics=["clicks"], dimensions=["platform"], ...)

    Args:
        core:       DataAgent instance (provides BSL models).
        bsl_models: BSL models dict (alternative to core).
        metrics:    List of metric names (e.g., ``["clicks"]`` or ``["revenue", "clicks"]``). At least one required; all must be from the same semantic model.
        dimensions: List of dimension names (e.g., ``["platform", "country"]``).
        filters:    List of filters (e.g. ``[{"field": "date", "op": ">=", "value": "2024-01-01"}, ...]``).
        time_grain: Optional time grain (``"day"``, ``"week"``, ``"month"``, ``"quarter"``, ``"year"``).
        limit:      Max rows to return.
        order_by:   Sort direction (``"asc"`` or ``"desc"``); sorts by first metric.

    Returns:
        WarehouseQueryResult with ``ok=True`` and ``data`` on success,
        or ``ok=False`` and ``error`` on failure.
    """
    models = (core.bsl_models if core is not None else bsl_models) or {}
    max_rows_per_query = 10000
    max_retries = 1
    retry_delay_seconds = 0.0
    if core is not None and hasattr(core, "_settings"):
        advanced = getattr(getattr(core, "_settings", None), "advanced", None)
        if advanced is not None:
            max_rows_per_query = int(getattr(advanced, "max_rows_per_query", 10000) or 10000)
            max_retries = max(1, int(getattr(advanced, "max_retries", 1) or 1))
            retry_delay_seconds = float(getattr(advanced, "retry_delay_seconds", 0) or 0)

    if not metrics or not isinstance(metrics, list) or not models:
        return WarehouseQueryResult(
            ok=False,
            data=[],
            error="metrics (non-empty list) and bsl_models/core required",
        )

    metrics = [m for m in metrics if m]
    if not metrics:
        return WarehouseQueryResult(
            ok=False,
            data=[],
            error="metrics (non-empty list) required",
        )

    try:
        # 1) Find which semantic model contains the first metric
        model_name = None
        model = None
        for name, m in models.items():
            measures = m.measures if hasattr(m, "measures") else (m.get("measures") or {})
            if metrics[0] in measures:
                model_name = name
                model = m
                break

        if model is None or not model_name:
            return WarehouseQueryResult(
                ok=False,
                data=[],
                error=f"Metric '{metrics[0]}' not found in any semantic model.",
            )

        # 2) Ensure all metrics are in the same model
        model_measures = model.measures if hasattr(model, "measures") else (model.get("measures") or {})
        for m in metrics:
            if m not in model_measures:
                return WarehouseQueryResult(
                    ok=False,
                    data=[],
                    error=f"All metrics must be from the same semantic model. '{m}' is not in model '{model_name}'.",
                )

        # 3) Build BSL query params
        bsl_filters = _agent_filters_to_bsl(filters) if filters else None
        bsl_order = _parse_order_by(order_by, metrics[0]) if order_by else None
        bsl_grain = _TIME_GRAIN_MAP.get((time_grain or "").lower()) if time_grain else None

        # 4) Execute via model.query() (BSL SemanticTable API)
        effective_limit = limit
        if effective_limit is None or effective_limit <= 0:
            effective_limit = max_rows_per_query
        else:
            effective_limit = min(int(effective_limit), max_rows_per_query)

        last_error: Exception | None = None
        query_result = None
        result_df = None
        for attempt in range(1, max_retries + 1):
            try:
                query_result = model.query(
                    dimensions=dimensions or [],
                    measures=metrics,
                    filters=bsl_filters,
                    order_by=bsl_order,
                    limit=effective_limit,
                    time_grain=bsl_grain,
                )
                result_df = query_result.execute()
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt < max_retries and retry_delay_seconds > 0:
                    time.sleep(retry_delay_seconds)

        if last_error is not None:
            raise last_error

        # 5) Convert DataFrame → list of dicts
        data = result_df.to_dict(orient="records") if result_df is not None else []

        return WarehouseQueryResult(
            ok=True,
            data=data,
            model=model_name,
            metrics=metrics,
            aggregate=query_result,
        )

    except Exception as e:
        return WarehouseQueryResult(
            ok=False,
            data=[],
            error=str(e),
        )


def _agent_filters_to_bsl(
    filters: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    """Convert agent filter list to BSL where clauses.

    Agent list: [{"field": "date", "op": ">=", "value": "2024-01-01"}, {"field": "date", "op": "<=", "value": "2024-12-31"}]
    BSL: [{"field": "date", "operator": ">=", "value": "..."}, ...]
    """
    if not filters or not isinstance(filters, list):
        return None

    bsl_filters: list[dict[str, Any]] = []
    for f in filters:
        if not isinstance(f, dict):
            continue
        field = f.get("dimension") or f.get("field")
        op_raw = f.get("op") or f.get("operator", "=")
        op = str(op_raw).strip().upper()
        val = f.get("value")

        if field is None or val is None:
            continue
        if op == "IN" and isinstance(val, list):
            bsl_filters.append({"field": field, "operator": "in", "values": val})
        elif op in (">=", "GTE"):
            bsl_filters.append({"field": field, "operator": ">=", "value": val})
        elif op in ("<=", "LTE"):
            bsl_filters.append({"field": field, "operator": "<=", "value": val})
        elif op in (">", "GT"):
            bsl_filters.append({"field": field, "operator": ">", "value": val})
        elif op in ("<", "LT"):
            bsl_filters.append({"field": field, "operator": "<", "value": val})
        elif op in ("=", "EQ", "EQUALS"):
            bsl_filters.append({"field": field, "operator": "equals", "value": val})
        else:
            bsl_filters.append({"field": field, "operator": "equals", "value": val})

    return bsl_filters if bsl_filters else None


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
        dims = m.get_dimensions() if hasattr(m, "get_dimensions") else {name: getattr(m, name) for name in m.dimensions} if hasattr(m, "dimensions") else (m.get("dimensions") or {})
        if dimension in dims:
            model_name = name
            model = m
            break

    if model is None or not model_name:
        return None

    # 2) Get a measure to run the query (we need at least one for BSL)
    measures = model.measures if hasattr(model, "measures") else model.get("measures", {})
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



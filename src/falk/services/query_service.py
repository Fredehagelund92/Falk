"""Shared query execution service used by LLM and MCP adapters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from falk.tools.calculations import compute_deltas, compute_shares, period_date_ranges
from falk.tools.warehouse import run_warehouse_query


@dataclass(frozen=True)
class QueryServiceResult:
    """Normalized result for query execution."""

    ok: bool
    data: list[dict[str, Any]]
    rows: int = 0
    metrics: list[str] | None = None
    model: str | None = None
    sql: str | None = None
    aggregate: Any = None
    period: str | None = None
    error: str | None = None
    error_code: str | None = None


def execute_query_metric(
    *,
    core: Any,
    metrics: list[str],
    dimensions: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    order_by: str | None = None,
    limit: int | None = None,
    time_grain: str | None = None,
    compare_period: str | None = None,
    include_share: bool = False,
) -> QueryServiceResult:
    """Execute metric query with optional period comparison and share calculation."""
    if not metrics:
        return QueryServiceResult(
            ok=False,
            data=[],
            error="At least one metric is required.",
            error_code="INVALID_ARGUMENT",
        )

    metric = metrics[0]

    if compare_period:
        if compare_period not in ("week", "month", "quarter"):
            return QueryServiceResult(
                ok=False,
                data=[],
                error=f"compare_period must be 'week', 'month', or 'quarter', got '{compare_period}'.",
                error_code="INVALID_ARGUMENT",
            )

        # compare_period is authoritative for time window; ignore user-provided date filters.
        (cur_start, cur_end), (prev_start, prev_end) = period_date_ranges(compare_period)
        date_filters_cur = [
            {"field": "date", "op": ">=", "value": cur_start},
            {"field": "date", "op": "<=", "value": cur_end},
        ]
        date_filters_prev = [
            {"field": "date", "op": ">=", "value": prev_start},
            {"field": "date", "op": "<=", "value": prev_end},
        ]

        cur_result = run_warehouse_query(
            core=core,
            metrics=metrics,
            dimensions=dimensions or [],
            filters=date_filters_cur,
            time_grain=time_grain,
            limit=limit,
            order_by=order_by,
        )
        prev_result = run_warehouse_query(
            core=core,
            metrics=metrics,
            dimensions=dimensions or [],
            filters=date_filters_prev,
            time_grain=time_grain,
            limit=limit,
            order_by=order_by,
        )
        if not cur_result.ok:
            return QueryServiceResult(
                ok=False,
                data=[],
                error=f"Current period query failed: {cur_result.error}",
                error_code="QUERY_FAILED",
            )
        if not prev_result.ok:
            return QueryServiceResult(
                ok=False,
                data=[],
                error=f"Previous period query failed: {prev_result.error}",
                error_code="QUERY_FAILED",
            )

        cur_data = cur_result.data or []
        prev_data = prev_result.data or []
        group_keys = dimensions or []
        if not group_keys and cur_data:
            group_keys = [k for k in cur_data[0].keys() if k != metric and k != "date"]
        deltas = compute_deltas(cur_data, prev_data, metric, group_keys) if (cur_data or prev_data) else []
        data = compute_shares(deltas, "current") if include_share else deltas
        return QueryServiceResult(
            ok=True,
            data=data,
            rows=len(data),
            metrics=metrics,
            model=cur_result.model,
            period=compare_period,
        )

    result = run_warehouse_query(
        core=core,
        metrics=metrics,
        dimensions=dimensions,
        filters=filters,
        time_grain=time_grain,
        limit=limit,
        order_by=order_by,
    )
    if not result.ok:
        return QueryServiceResult(
            ok=False,
            data=[],
            error=f"Query failed: {result.error}",
            error_code="QUERY_FAILED",
        )
    data = result.data or []
    if include_share:
        data = compute_shares(data, metric)
    return QueryServiceResult(
        ok=True,
        data=data,
        rows=len(data),
        metrics=result.metrics,
        model=result.model,
        sql=result.sql,
        aggregate=getattr(result, "aggregate", None),
    )

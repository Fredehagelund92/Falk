"""Reusable data-quality helpers built on top of the data agent.

This module centralises data-quality logic so it can be used from:

- The Typer-based CLI (primary contract for automations / agent skills)
- The MCP server (interactive exploration from tools like Cursor / Claude)
- Tests and future orchestrators

Each check returns a structured ``QualityResult`` object so callers can choose
between human-readable text and machine-friendly JSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Iterable

from falk.agent import DataAgent
from falk.tools.calculations import period_date_ranges
from falk.tools.warehouse import run_warehouse_query


@dataclass
class QualityResult:
    """Structured result of a quality check.

    Attributes:
        ok: True if the check passed or is informational, False on failure.
        name: Machine-friendly check name (e.g. ``"metric_freshness"``).
        summary: One-line human-readable summary.
        details: Optional structured payload with extra info.
    """

    ok: bool
    name: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


def quality_result_to_dict(result: QualityResult) -> dict[str, Any]:
    """Convert a ``QualityResult`` to a plain dict (JSON-serialisable)."""
    return asdict(result)


def format_quality_result_text(result: QualityResult) -> str:
    """Format a ``QualityResult`` as a human-readable message."""
    lines = [result.summary]
    if result.details:
        # For now we only show a few high-signal fields, callers can override.
        meta = result.details.get("meta") or {}
        if meta:
            lines.append("")
            for k, v in meta.items():
                lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def _get_falk() -> DataAgent | None:
    """Get a DataAgent instance for querying metrics and dimensions."""
    try:
        return DataAgent()
    except Exception:
        # Callers will surface a user-friendly error
        return None


def _query_metric(
    metric: str,
    *,
    group_by: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    time_grain: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Low-level helper to query a metric via the warehouse.

    Returns:
        ``{"ok": bool, "data": list[dict], "error": str | None}``.
    """
    agent = _get_falk()
    if not agent:
        return {"ok": False, "error": "DataAgent not available"}

    try:
        query_obj: dict[str, Any] = {"metric": metric}
        if group_by:
            query_obj["dimensions"] = group_by
        if filters:
            query_obj["filters"] = filters
        if time_grain:
            query_obj["time_grain"] = time_grain
        if limit:
            query_obj["limit"] = limit

        result = run_warehouse_query(
            bsl_models=agent.bsl_models,
            query_object=query_obj,
        )

        if result.ok:
            return {"ok": True, "data": result.data, "error": None}
        return {"ok": False, "data": [], "error": result.error or "Query failed"}
    except Exception as e:
        return {"ok": False, "data": [], "error": str(e)}


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_metric_freshness(
    metric: str,
    *,
    expected_frequency: str = "daily",
    max_age_hours: int | None = None,
) -> QualityResult:
    """Check if a metric has recent data (freshness check)."""
    # Set default max_age based on frequency
    if max_age_hours is None:
        defaults = {"hourly": 2, "daily": 26, "weekly": 170}
        max_age_hours = defaults.get(expected_frequency.lower(), 26)

    # Query the most recent data point
    result = _query_metric(
        metric=metric,
        group_by=["date"] if expected_frequency != "hourly" else None,
        time_grain=(
            "day"
            if expected_frequency == "daily"
            else "hour"
            if expected_frequency == "hourly"
            else "week"
        ),
        limit=1,
        filters=[{"dimension": "date", "op": "<=", "value": datetime.now().strftime("%Y-%m-%d")}],
    )

    if not result.get("ok"):
        return QualityResult(
            ok=False,
            name="metric_freshness",
            summary=f"❌ Failed to check freshness for {metric}: {result.get('error', 'Unknown error')}",
        )

    data: list[dict[str, Any]] = result.get("data") or []
    if not data:
        return QualityResult(
            ok=False,
            name="metric_freshness",
            summary=f"⚠️  {metric} has no recent data. Metric may be stale or not configured.",
        )

    latest_row = data[0]
    latest_date_str: Any = (
        latest_row.get("period")
        or latest_row.get("date")
        or latest_row.get("date_day")
    )
    if not latest_date_str:
        # Try to find any date-like key
        for key, val in latest_row.items():
            if "date" in key.lower() or "period" in key.lower():
                latest_date_str = str(val)
                break

    if not latest_date_str:
        return QualityResult(
            ok=False,
            name="metric_freshness",
            summary=f"⚠️  Could not determine latest date for {metric}.",
            details={"row": latest_row},
        )

    try:
        # Parse date (handle various formats)
        if isinstance(latest_date_str, str):
            try:
                latest_date = datetime.fromisoformat(latest_date_str.replace("Z", "+00:00"))
            except ValueError:
                latest_date = datetime.strptime(latest_date_str[:10], "%Y-%m-%d")
        else:
            latest_date = latest_date_str

        age_hours = (datetime.now() - latest_date.replace(tzinfo=None)).total_seconds() / 3600

        ok = age_hours <= max_age_hours
        if ok:
            summary = (
                f"✅ {metric} is fresh. "
                f"Latest data: {latest_date_str} ({age_hours:.1f} hours ago, max: {max_age_hours}h)"
            )
        else:
            summary = (
                f"❌ {metric} is STALE. "
                f"Latest data: {latest_date_str} ({age_hours:.1f} hours ago, max: {max_age_hours}h). "
                f"Expected {expected_frequency} updates."
            )

        return QualityResult(
            ok=ok,
            name="metric_freshness",
            summary=summary,
            details={
                "meta": {
                    "metric": metric,
                    "latest_date": str(latest_date_str),
                    "age_hours": age_hours,
                    "max_age_hours": max_age_hours,
                    "expected_frequency": expected_frequency,
                }
            },
        )
    except Exception as e:
        return QualityResult(
            ok=False,
            name="metric_freshness",
            summary=f"⚠️  Error parsing date '{latest_date_str}': {e}",
        )


def validate_dimension_values(
    dimension: str,
    *,
    allowed_values: Iterable[str] | None = None,
    metric: str | None = None,
) -> QualityResult:
    """Validate that dimension values match an allowed set."""
    agent = _get_falk()
    if not agent:
        return QualityResult(
            ok=False,
            name="dimension_values",
            summary="❌ DataAgent not available",
        )

    # Find a metric if not provided
    if not metric:
        metrics_result = agent.list_metrics()
        models = metrics_result.get("semantic_models", {}) or {}
        if models:
            first_model = list(models.values())[0]
            if first_model:
                metric = first_model[0].get("name")
        if not metric:
            return QualityResult(
                ok=False,
                name="dimension_values",
                summary="❌ No metric available for validation query",
            )

    # Query distinct dimension values
    result = _query_metric(
        metric=metric,
        group_by=[dimension],
        limit=1000,
    )

    if not result.get("ok"):
        return QualityResult(
            ok=False,
            name="dimension_values",
            summary=f"❌ Failed to query {dimension}: {result.get('error', 'Unknown error')}",
        )

    data: list[dict[str, Any]] = result.get("data") or []
    actual_values = {
        str(row.get(dimension, ""))
        for row in data
        if row.get(dimension) is not None
    }

    if allowed_values is None:
        values_list = sorted(actual_values)
        summary = (
            f"📊 Found {len(values_list)} distinct values for {dimension}."
        )
        return QualityResult(
            ok=True,
            name="dimension_values",
            summary=summary,
            details={
                "meta": {
                    "dimension": dimension,
                    "metric": metric,
                    "distinct_values": len(values_list),
                },
                "values": values_list,
            },
        )

    allowed_set = {str(v).strip() for v in allowed_values}
    invalid = sorted(actual_values - allowed_set)
    missing = sorted(allowed_set - actual_values)
    valid = sorted(actual_values & allowed_set)

    ok = not invalid and not missing
    if ok:
        summary = f"✅ All {len(valid)} values for {dimension} are valid."
    else:
        summary = (
            f"📊 Validation results for {dimension}: "
            f"{len(valid)} valid, {len(invalid)} invalid, {len(missing)} missing."
        )

    return QualityResult(
        ok=ok,
        name="dimension_values",
        summary=summary,
        details={
            "meta": {
                "dimension": dimension,
                "metric": metric,
                "valid_count": len(valid),
                "invalid_count": len(invalid),
                "missing_count": len(missing),
            },
            "valid": valid,
            "invalid": invalid,
            "missing": missing,
        },
    )


def detect_anomalies(
    metric: str,
    *,
    threshold_pct: float = 20.0,
    period: str = "week",
    group_by: list[str] | None = None,
) -> QualityResult:
    """Detect anomalies by comparing current period to previous period."""
    agent = _get_falk()
    if not agent:
        return QualityResult(
            ok=False,
            name="anomalies",
            summary="❌ DataAgent not available",
        )

    try:
        (cur_start, cur_end), (prev_start, prev_end) = period_date_ranges(period)

        def _run(start: str, end: str):
            q: dict[str, Any] = {
                "metric": metric,
                "filters": [
                    {"dimension": "date", "op": ">=", "value": start},
                    {"dimension": "date", "op": "<=", "value": end},
                ],
            }
            if group_by:
                q["dimensions"] = group_by
            return run_warehouse_query(
                bsl_models=agent.bsl_models,
                query_object=q,
            )

        cur_result = _run(cur_start, cur_end)
        prev_result = _run(prev_start, prev_end)

        if not cur_result.ok:
            return QualityResult(
                ok=False,
                name="anomalies",
                summary=f"❌ Failed to query current period: {cur_result.error}",
            )
        if not prev_result.ok:
            return QualityResult(
                ok=False,
                name="anomalies",
                summary=f"❌ Failed to query previous period: {prev_result.error}",
            )

        cur_data = cur_result.data or []
        prev_data = prev_result.data or []

        if not cur_data:
            return QualityResult(
                ok=True,
                name="anomalies",
                summary=(
                    f"⚠️  No data for {metric} in current {period} "
                    f"({cur_start} to {cur_end})"
                ),
            )

        anomalies: list[dict[str, Any]] = []
        cur_dict = {
            tuple(row.get(d, "") for d in (group_by or [])): row.get(metric, 0)
            for row in cur_data
        }
        prev_dict = {
            tuple(row.get(d, "") for d in (group_by or [])): row.get(metric, 0)
            for row in prev_data
        }

        for key in cur_dict:
            cur_val = cur_dict[key]
            prev_val = prev_dict.get(key, 0)
            if prev_val == 0:
                continue
            pct_change = abs((cur_val - prev_val) / prev_val * 100)
            if pct_change >= threshold_pct:
                anomalies.append(
                    {
                        "key": key,
                        "current": cur_val,
                        "previous": prev_val,
                        "pct_change": pct_change,
                    }
                )

        period_labels = {
            "day": "today vs yesterday",
            "week": "this week vs last week",
            "month": "this month vs last month",
        }
        label = period_labels.get(period, f"current vs previous {period}")

        if not anomalies:
            summary = (
                f"✅ No anomalies detected for {metric} ({label}). "
                f"All changes are within {threshold_pct}% threshold."
            )
            return QualityResult(
                ok=True,
                name="anomalies",
                summary=summary,
                details={
                    "meta": {
                        "metric": metric,
                        "period": period,
                        "threshold_pct": threshold_pct,
                        "anomalies": 0,
                    }
                },
            )

        # Sort by largest change
        anomalies_sorted = sorted(
            anomalies,
            key=lambda x: x["pct_change"],
            reverse=True,
        )

        summary = (
            f"🚨 Found {len(anomalies)} anomaly(ies) for {metric} ({period})."
        )

        return QualityResult(
            ok=False,
            name="anomalies",
            summary=summary,
            details={
                "meta": {
                    "metric": metric,
                    "period": period,
                    "threshold_pct": threshold_pct,
                    "anomalies": len(anomalies),
                },
                "anomalies": anomalies_sorted,
            },
        )
    except Exception as e:
        return QualityResult(
            ok=False,
            name="anomalies",
            summary=f"❌ Error detecting anomalies: {e}",
        )


def check_data_completeness(
    metric: str,
    *,
    dimension: str,
    expected_values: Iterable[str] | None = None,
    time_grain: str = "day",
    days_back: int = 7,
) -> QualityResult:
    """Check that all expected dimension values have data (completeness)."""
    # Get date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    result = _query_metric(
        metric=metric,
        group_by=[dimension, "date"],
        time_grain=time_grain,
        filters=[
            {"dimension": "date", "op": ">=", "value": start_str},
            {"dimension": "date", "op": "<=", "value": end_str},
        ],
    )

    if not result.get("ok"):
        return QualityResult(
            ok=False,
            name="completeness",
            summary=f"❌ Failed to check completeness: {result.get('error', 'Unknown error')}",
        )

    data: list[dict[str, Any]] = result.get("data") or []
    if not data:
        return QualityResult(
            ok=False,
            name="completeness",
            summary=f"⚠️  No data found for {metric} in the last {days_back} days.",
        )

    period_key = "period" if time_grain else "date"
    actual_combos = {
        (str(row.get(dimension, "")), str(row.get(period_key, "")))
        for row in data
        if row.get(dimension) is not None and row.get(period_key) is not None
    }

    if expected_values is None:
        expected_values = sorted({combo[0] for combo in actual_combos})

    expected_values_list = list(expected_values)
    periods = sorted({combo[1] for combo in actual_combos})

    expected_combos = {
        (val, period) for val in expected_values_list for period in periods
    }
    missing = expected_combos - actual_combos

    if not missing:
        summary = (
            f"✅ All expected combinations for {metric} by {dimension} "
            f"have data over the last {days_back} days."
        )
        return QualityResult(
            ok=True,
            name="completeness",
            summary=summary,
            details={
                "meta": {
                    "metric": metric,
                    "dimension": dimension,
                    "days_back": days_back,
                    "expected_combinations": len(expected_combos),
                    "actual_combinations": len(actual_combos),
                    "missing_combinations": 0,
                }
            },
        )

    # Group by dimension value
    by_value: dict[str, list[str]] = {}
    for val, period in sorted(missing):
        by_value.setdefault(val, []).append(period)

    summary = (
        f"❌ Missing {len(missing)} combination(s) for {metric} by {dimension} "
        f"over the last {days_back} days."
    )

    return QualityResult(
        ok=False,
        name="completeness",
        summary=summary,
        details={
            "meta": {
                "metric": metric,
                "dimension": dimension,
                "days_back": days_back,
                "expected_combinations": len(expected_combos),
                "actual_combinations": len(actual_combos),
                "missing_combinations": len(missing),
            },
            "missing_by_value": by_value,
        },
    )




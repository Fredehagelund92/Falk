"""Analytics calculation helpers.

Pure functions for computing derived analytics on query results.
Used by agent tools (pydantic_agent.py) to provide richer responses.

Add new calculation helpers here — this is the place for any reusable
analytics logic (shares, deltas, moving averages, etc.).

Functions
---------
- ``compute_shares``              — add percentage-of-total to each row
- ``compute_deltas``              — compare current vs previous period per group
- ``period_date_ranges``          — compute date ranges for "this vs last week/month/quarter"
- ``calculate_variance_explained`` — calculate how much variance a dimension explains
- ``rank_dimensions_by_impact``    — rank dimensions by their impact on metric change
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Percentage shares
# ---------------------------------------------------------------------------

def compute_shares(
    data: list[dict[str, Any]],
    metric: str,
) -> list[dict[str, Any]]:
    """Add ``share_pct`` (percentage of total) to each row.

    Example::

        >>> compute_shares([{"p": "A", "clicks": 75}, {"p": "B", "clicks": 25}], "clicks")
        [{'p': 'A', 'clicks': 75, 'share_pct': 75.0}, {'p': 'B', 'clicks': 25, 'share_pct': 25.0}]
    """
    total = sum(_safe_float(row.get(metric)) for row in data)
    if total == 0:
        return [{**row, "share_pct": 0.0} for row in data]
    return [
        {**row, "share_pct": round(_safe_float(row.get(metric)) / total * 100, 1)}
        for row in data
    ]


# ---------------------------------------------------------------------------
# Period-over-period comparison
# ---------------------------------------------------------------------------

def compute_deltas(
    current: list[dict[str, Any]],
    previous: list[dict[str, Any]],
    metric: str,
    group_keys: list[str],
) -> list[dict[str, Any]]:
    """Compare current vs previous data, returning delta and % change per group.

    Args:
        current:    Current-period rows (already aggregated).
        previous:   Previous-period rows (already aggregated).
        metric:     The metric column name.
        group_keys: Dimension columns used to match rows between periods.

    Returns:
        One dict per group with keys: *group_keys*, ``current``, ``previous``,
        ``delta``, ``pct_change`` (None if previous was 0).
    """
    def _key(row: dict) -> str:
        return "|".join(str(row.get(k, "")) for k in group_keys)

    prev_map = {_key(r): _safe_float(r.get(metric)) for r in previous}

    result: list[dict[str, Any]] = []
    for row in current:
        key = _key(row)
        cur_val = _safe_float(row.get(metric))
        prev_val = prev_map.get(key, 0.0)
        delta = cur_val - prev_val
        pct = round(delta / prev_val * 100, 1) if prev_val else None

        result.append({
            **{k: row.get(k) for k in group_keys},
            "current": cur_val,
            "previous": prev_val,
            "delta": delta,
            "pct_change": pct,
        })
    return result


# ---------------------------------------------------------------------------
# Date range calculation
# ---------------------------------------------------------------------------

def period_date_ranges(
    period: str,
    reference: date | None = None,
) -> tuple[tuple[str, str], tuple[str, str]]:
    """Compute current and previous date ranges for a named period.

    Args:
        period:    ``"week"``, ``"month"``, or ``"quarter"``.
        reference: Override "today" (useful for testing).

    Returns:
        ``((cur_start, cur_end), (prev_start, prev_end))`` as ISO strings.

    The "previous" range always has the *same number of days* as the current
    range so the comparison is apples-to-apples.
    """
    today = reference or date.today()

    if period == "week":
        cur_start = today - timedelta(days=today.weekday())  # Monday
        cur_end = today
        prev_start = cur_start - timedelta(weeks=1)
        prev_end = cur_end - timedelta(weeks=1)

    elif period == "month":
        cur_start = today.replace(day=1)
        cur_end = today
        if today.month == 1:
            prev_start = today.replace(year=today.year - 1, month=12, day=1)
        else:
            prev_start = today.replace(month=today.month - 1, day=1)
        days_in = (today - cur_start).days
        prev_end = prev_start + timedelta(days=days_in)

    elif period == "quarter":
        q_month = ((today.month - 1) // 3) * 3 + 1
        cur_start = today.replace(month=q_month, day=1)
        cur_end = today
        if q_month <= 3:
            prev_start = today.replace(year=today.year - 1, month=q_month + 9, day=1)
        else:
            prev_start = today.replace(month=q_month - 3, day=1)
        days_in = (today - cur_start).days
        prev_end = prev_start + timedelta(days=days_in)

    else:
        raise ValueError(
            f"Unsupported period '{period}'. Use 'week', 'month', or 'quarter'."
        )

    return (
        (cur_start.isoformat(), cur_end.isoformat()),
        (prev_start.isoformat(), prev_end.isoformat()),
    )


def suggest_date_range(
    period: str,
    reference: date | None = None,
) -> dict[str, str]:
    """Compute a single date range for common periods.

    Args:
        period: One of: yesterday, today, last_7_days, last_30_days, this_week,
                this_month, last_month, this_quarter.
        reference: Override "today" (useful for testing).

    Returns:
        {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
    """
    today = reference or date.today()

    if period == "yesterday":
        d = today - timedelta(days=1)
        return {"start": d.isoformat(), "end": d.isoformat()}

    if period == "today":
        return {"start": today.isoformat(), "end": today.isoformat()}

    if period == "last_7_days":
        start = today - timedelta(days=6)
        return {"start": start.isoformat(), "end": today.isoformat()}

    if period == "last_30_days":
        start = today - timedelta(days=29)
        return {"start": start.isoformat(), "end": today.isoformat()}

    if period == "this_week":
        start = today - timedelta(days=today.weekday())
        return {"start": start.isoformat(), "end": today.isoformat()}

    if period == "this_month":
        start = today.replace(day=1)
        return {"start": start.isoformat(), "end": today.isoformat()}

    if period == "last_month":
        if today.month == 1:
            start = today.replace(year=today.year - 1, month=12, day=1)
        else:
            start = today.replace(month=today.month - 1, day=1)
        end = today.replace(day=1) - timedelta(days=1)
        return {"start": start.isoformat(), "end": end.isoformat()}

    if period == "this_quarter":
        q_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=q_month, day=1)
        return {"start": start.isoformat(), "end": today.isoformat()}

    raise ValueError(
        f"Unsupported period '{period}'. Use: yesterday, today, last_7_days, "
        "last_30_days, this_week, this_month, last_month, this_quarter."
    )


# ---------------------------------------------------------------------------
# Metric decomposition and variance analysis
# ---------------------------------------------------------------------------

def calculate_variance_explained(
    total_delta: float,
    dimension_deltas: list[dict[str, Any]],
    metric_key: str = "delta",
) -> list[dict[str, Any]]:
    """Calculate how much variance each dimension value explains.
    
    Args:
        total_delta: Overall metric change (current - previous)
        dimension_deltas: List of deltas per dimension value (from compute_deltas)
        metric_key: Key for the delta value (default: "delta")
    
    Returns:
        List of dimension values with added fields:
        - variance_explained: Absolute contribution to total change
        - variance_pct: % of total variance explained
        - impact_rank: 1 = highest impact
    
    Example:
        Total revenue delta: +$100k
        - Region A: +$70k → 70% variance explained
        - Region B: +$30k → 30% variance explained
        - Region C: -$20k → -20% variance explained
    """
    if abs(total_delta) < 0.01:  # Near-zero change
        return [{**d, "variance_explained": 0.0, "variance_pct": 0.0, "impact_rank": 0} 
                for d in dimension_deltas]
    
    # Calculate variance contribution for each value
    enriched = []
    for d in dimension_deltas:
        delta = _safe_float(d.get(metric_key, 0))
        variance_explained = delta  # Absolute contribution
        variance_pct = (delta / total_delta * 100) if total_delta != 0 else 0.0
        
        enriched.append({
            **d,
            "variance_explained": variance_explained,
            "variance_pct": variance_pct,
        })
    
    # Rank by absolute impact (largest changes first, regardless of direction)
    enriched.sort(key=lambda x: abs(x.get("variance_explained", 0)), reverse=True)
    for idx, item in enumerate(enriched, 1):
        item["impact_rank"] = idx
    
    return enriched


def rank_dimensions_by_impact(
    current: list[dict[str, Any]],
    previous: list[dict[str, Any]],
    metric: str,
    dimensions: list[str],
    total_delta: float,
) -> list[dict[str, Any]]:
    """Rank dimensions by how much they explain the metric change.
    
    For each dimension, calculates the sum of absolute deltas and determines
    what % of total variance it explains.
    
    Args:
        current: Current period data
        previous: Previous period data
        metric: Metric name
        dimensions: Available dimension names
        total_delta: Overall metric change
    
    Returns:
        List of dicts with:
        - dimension: Dimension name
        - variance_explained_pct: % of variance explained
        - impact_score: Weighted impact score
    
    Example:
        Revenue +$100k total change
        - region: explains 70% (North America +$70k, others small)
        - product: explains 85% (Product A +$60k, Product B +$25k, etc.)
        - customer_segment: explains 40% (small changes across segments)
        
        Result: [product (85%), region (70%), customer_segment (40%)]
    """
    if abs(total_delta) < 0.01:
        return [{"dimension": d, "variance_explained_pct": 0.0, "impact_score": 0.0} 
                for d in dimensions]
    
    dimension_impacts = []
    
    for dim in dimensions:
        # Skip if dimension doesn't exist in data
        if not any(dim in row for row in current):
            continue
        
        # Compute deltas for this dimension
        deltas = compute_deltas(current, previous, metric, [dim])
        
        # Sum absolute deltas (total movement in this dimension)
        total_movement = sum(abs(_safe_float(d.get("delta", 0))) for d in deltas)
        
        # Calculate variance explained
        # High movement relative to total change = high explanation power
        variance_pct = (total_movement / abs(total_delta)) * 100 if total_delta != 0 else 0.0
        
        # Impact score (normalize to 0-100 scale)
        # Dimensions that move a lot relative to the total change get high scores
        impact_score = min(variance_pct, 100.0)
        
        dimension_impacts.append({
            "dimension": dim,
            "variance_explained_pct": round(variance_pct, 1),
            "impact_score": round(impact_score, 1),
            "total_movement": round(total_movement, 2),
        })
    
    # Sort by impact score
    dimension_impacts.sort(key=lambda x: x["impact_score"], reverse=True)
    
    return dimension_impacts


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_float(val: Any) -> float:
    """Convert a value to float, defaulting to 0."""
    try:
        return float(val) if val is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


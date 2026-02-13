"""Plotly chart generation for data visualization.

Generates interactive HTML charts and static PNG images suitable for Slack uploads.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import plotly.colors as pcol
    import plotly.graph_objects as go
    import plotly.io as pio
    PLOTLY_AVAILABLE = True
except ImportError:
    pcol = None
    PLOTLY_AVAILABLE = False

# Plotly color scale for charts
CHART_COLORSCALE = "blugrn"


def generate_bar_chart(
    data: list[dict[str, Any]],
    metric: str,
    dimension: str,
    title: str | None = None,
    max_bars: int = 20,
) -> tuple[str, Path | None]:
    """Generate a bar chart from query data.

    Args:
        data: List of dicts with metric and dimension values.
        metric: Metric column name.
        dimension: Dimension column name.
        title: Chart title (auto-generated if None).
        max_bars: Max number of bars to show.

    Returns:
        Tuple of (status_message, filepath) where filepath is None if failed.
    """
    if not PLOTLY_AVAILABLE:
        return (
            "Chart generation requires Plotly. Install it with: uv sync",
            None,
        )

    if not data:
        return ("No data to chart.", None)

    # Sort by metric value (descending) and take top N
    sorted_data = sorted(data, key=lambda r: float(r.get(metric, 0) or 0), reverse=True)
    top_data = sorted_data[:max_bars]

    dim_values = [str(row.get(dimension, "")) for row in top_data]
    metric_values = [float(row.get(metric, 0) or 0) for row in top_data]

    fig = go.Figure(
        data=[
            go.Bar(
                x=dim_values,
                y=metric_values,
                text=[f"{v:,.0f}" for v in metric_values],
                textposition="outside",
                marker=dict(
                    color=metric_values,
                    colorscale=CHART_COLORSCALE,
                    showscale=False,
                ),
            )
        ]
    )

    fig.update_layout(
        title=title or f"{metric} by {dimension}",
        xaxis_title=dimension,
        yaxis_title=metric,
        height=500,
        showlegend=False,
        template="plotly_white",
    )

    return _save_chart(fig, f"bar_{metric}_{dimension}")


def generate_line_chart(
    data: list[dict[str, Any]],
    metric: str,
    time_dimension: str,
    title: str | None = None,
) -> tuple[str, Path | None]:
    """Generate a line chart for time series data.

    Args:
        data: List of dicts, should be sorted by time_dimension.
        metric: Metric column name.
        time_dimension: Time dimension column name.
        title: Chart title (auto-generated if None).

    Returns:
        Tuple of (status_message, filepath) where filepath is None if failed.
    """
    if not PLOTLY_AVAILABLE:
        return (
            "Chart generation requires Plotly. Install it with: uv sync",
            None,
        )

    if not data:
        return ("No data to chart.", None)

    # Sort by time dimension if not already sorted
    sorted_data = sorted(data, key=lambda r: str(r.get(time_dimension, "")))

    time_values = [str(row.get(time_dimension, "")) for row in sorted_data]
    metric_values = [float(row.get(metric, 0) or 0) for row in sorted_data]

    # Use blugrn scale — sample middle color for line
    line_color = pcol.sample_colorscale(CHART_COLORSCALE, [0.5])[0]

    fig = go.Figure(
        data=[
            go.Scatter(
                x=time_values,
                y=metric_values,
                mode="lines+markers",
                line=dict(color=line_color, width=2),
                marker=dict(size=6, color=line_color),
            )
        ]
    )

    fig.update_layout(
        title=title or f"{metric} over time",
        xaxis_title=time_dimension,
        yaxis_title=metric,
        height=500,
        showlegend=False,
        template="plotly_white",
    )

    return _save_chart(fig, f"line_{metric}_{time_dimension}")


def generate_pie_chart(
    data: list[dict[str, Any]],
    metric: str,
    dimension: str,
    title: str | None = None,
    max_slices: int = 15,
) -> tuple[str, Path | None]:
    """Generate a pie chart from query data.

    Args:
        data: List of dicts with metric and dimension values.
        metric: Metric column name.
        dimension: Dimension column name.
        title: Chart title (auto-generated if None).
        max_slices: Max number of slices to show (others grouped as "Other").

    Returns:
        Tuple of (status_message, filepath) where filepath is None if failed.
    """
    if not PLOTLY_AVAILABLE:
        return (
            "Chart generation requires Plotly. Install it with: uv sync",
            None,
        )

    if not data:
        return ("No data to chart.", None)

    # Sort by metric value (descending)
    sorted_data = sorted(data, key=lambda r: float(r.get(metric, 0) or 0), reverse=True)

    if len(sorted_data) > max_slices:
        top_data = sorted_data[:max_slices]
        other_total = sum(float(r.get(metric, 0) or 0) for r in sorted_data[max_slices:])
        if other_total > 0:
            top_data.append({dimension: "Other", metric: other_total})
    else:
        top_data = sorted_data

    labels = [str(row.get(dimension, "")) for row in top_data]
    values = [float(row.get(metric, 0) or 0) for row in top_data]

    # Sample discrete colors from blugrn scale for pie slices
    n = len(labels)
    sample_pts = [i / max(n - 1, 1) for i in range(n)]
    slice_colors = pcol.sample_colorscale(CHART_COLORSCALE, sample_pts)
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                textinfo="label+percent",
                textposition="outside",
                marker=dict(colors=slice_colors),
            )
        ]
    )

    fig.update_layout(
        title=title or f"{metric} by {dimension}",
        height=500,
        template="plotly_white",
    )

    return _save_chart(fig, f"pie_{metric}_{dimension}")


def suggest_chart_type(
    data: list[dict[str, Any]],
    dimension: str,
    group_by: list[str],
    bsl_models: dict[str, Any],
) -> str:
    """Auto-detect the best chart type based on data characteristics.

    Rules:
    - Time dimension → "line" (shows trends over time)
    - 2-8 categories → "pie" (good for showing shares)
    - 9+ categories → "bar" (better readability)

    Args:
        data: Query result data.
        dimension: The dimension being charted.
        group_by: All dimensions in the query.
        bsl_models: BSL SemanticModel objects (for checking if dimension is time-based).

    Returns:
        "bar", "line", or "pie"
    """
    # Check if dimension is a time dimension in any BSL model
    for model_name, model in bsl_models.items():
        dims = model.get_dimensions()
        if dimension in dims and dims[dimension].is_time_dimension:
            return "line"

    # Check dimension name patterns (fallback if not in BSL metadata)
    time_patterns = ("date", "period", "time", "month", "week", "day", "year")
    if any(pattern in dimension.lower() for pattern in time_patterns):
        return "line"

    # Count unique values in the dimension
    unique_values = len(set(str(row.get(dimension, "")) for row in data if row.get(dimension) is not None))

    # Pie charts work well for 2-8 categories (shows shares nicely)
    if 2 <= unique_values <= 8:
        return "pie"

    # Bar charts for everything else (better for many categories)
    return "bar"


def _save_chart(fig: Any, base_name: str) -> tuple[str, Path | None]:
    """Save a Plotly figure as PNG and return the filepath."""
    try:
        from datetime import datetime

        export_dir = Path.cwd() / "exports" / "charts"
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{base_name}_{timestamp}.png"
        filepath = export_dir / filename

        # Save as PNG (for Slack upload)
        # Note: requires kaleido package for PNG export
        try:
            fig.write_image(str(filepath), width=1200, height=600, scale=2)
        except ValueError as e:
            if "kaleido" in str(e).lower():
                return (
                    "PNG export requires 'kaleido'. Install it with: uv sync",
                    None,
                )
            raise

        return (f"Chart saved to {filepath}", filepath)
    except Exception as e:
        return (f"Failed to save chart: {e}", None)


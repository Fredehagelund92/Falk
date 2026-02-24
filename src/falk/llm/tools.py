"""Toolset definitions used by the Pydantic AI agent."""

from __future__ import annotations

import importlib.util
import logging
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic_ai import FunctionToolset, RunContext

from falk.access import (
    allowed_dimensions,
    allowed_metrics,
    filter_dimensions,
    filter_metrics,
    is_dimension_allowed,
    is_metric_allowed,
)
from falk.agent import DataAgent
from falk.llm.results import tool_error
from falk.llm.state import (
    access_cfg,
    get_runtime_state,
    save_runtime_state,
    user_id,
)
from falk.services.query_service import execute_query_metric
from falk.tools.calculations import suggest_date_range as _suggest_date_range

if TYPE_CHECKING:
    from falk.settings import ToolExtensionConfig

logger = logging.getLogger(__name__)

data_tools = FunctionToolset()

_TOOLSET_ATTR_NAMES = ("toolset", "data_tools", "tools")


def load_custom_toolsets(
    project_root: Path,
    extensions: list[ToolExtensionConfig],
) -> list[FunctionToolset]:
    """Load custom tool modules from project and return validated FunctionToolset instances.

    Each module must export a FunctionToolset (as 'toolset', 'data_tools', or 'tools').
    Invalid or missing modules log warnings and are skipped; built-in tools remain available.
    """
    if not extensions:
        return []

    project_root = project_root.resolve()
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    result: list[FunctionToolset] = []
    for ext in extensions:
        if not ext.enabled:
            continue
        mod_name = ext.module.strip()
        if not mod_name:
            continue
        try:
            spec = importlib.util.find_spec(mod_name)
            if spec is None or spec.origin is None:
                logger.warning("Extension module not found: %s", mod_name)
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
        except Exception as e:
            logger.warning("Failed to load extension module %s: %s", mod_name, e)
            continue

        toolset = None
        for attr in _TOOLSET_ATTR_NAMES:
            obj = getattr(mod, attr, None)
            if isinstance(obj, FunctionToolset):
                toolset = obj
                break
        if toolset is None:
            for _name, obj in vars(mod).items():
                if isinstance(obj, FunctionToolset):
                    toolset = obj
                    break
        if toolset is None:
            logger.warning(
                "Extension module %s has no FunctionToolset (expected toolset, data_tools, or tools)",
                mod_name,
            )
            continue
        result.append(toolset)
    return result


@data_tools.tool
def list_catalog(ctx: RunContext[DataAgent], entity_type: str = "both") -> dict[str, Any]:
    """List metrics and/or dimensions. entity_type: metric | dimension | both."""
    et = (entity_type or "both").strip().lower()
    if et not in ("metric", "dimension", "both"):
        return tool_error(
            f"entity_type must be 'metric', 'dimension', or 'both', got '{entity_type}'.",
            "INVALID_ENTITY_TYPE",
        )

    result: dict[str, Any] = {}
    allowed_m = allowed_metrics(user_id(ctx), access_cfg(ctx))
    allowed_d = allowed_dimensions(user_id(ctx), access_cfg(ctx))

    if et in ("metric", "both"):
        metrics = ctx.deps.list_metrics().get("metrics", [])
        result["metrics"] = filter_metrics(metrics, allowed_m)
    if et in ("dimension", "both"):
        dimensions = ctx.deps.list_dimensions().get("dimensions", [])
        result["dimensions"] = filter_dimensions(dimensions, allowed_d)

    return result


@data_tools.tool
def suggest_date_range(ctx: RunContext[DataAgent], period: str) -> dict[str, str] | dict[str, Any]:
    """Get date range for common periods. period: last_7_days, last_30_days, this_month, etc."""
    try:
        return _suggest_date_range(period)
    except ValueError as e:
        return tool_error(str(e), "INVALID_DATE_PERIOD")


@data_tools.tool
def describe_metric(ctx: RunContext[DataAgent], name: str) -> str | dict[str, Any]:
    """Get full description of a metric (measure) including dimensions and time grains."""
    allowed = allowed_metrics(user_id(ctx), access_cfg(ctx))
    if not is_metric_allowed(name, allowed):
        return tool_error(
            f"Metric '{name}' not found. Use list_catalog to see available metrics.",
            "METRIC_NOT_FOUND",
        )
    return ctx.deps.describe_metric(name)


@data_tools.tool
def describe_model(ctx: RunContext[DataAgent], name: str) -> dict[str, Any] | str:
    """Get full description of a semantic model (metrics, dimensions, time grains)."""
    return ctx.deps.describe_model(name)


@data_tools.tool
def describe_dimension(ctx: RunContext[DataAgent], name: str) -> str:
    """Get full description of a dimension (type, description, domain)."""
    return ctx.deps.describe_dimension(name)


@data_tools.tool
def lookup_values(
    ctx: RunContext[DataAgent],
    dimension: str,
    search: str | None = None,
) -> list[str] | dict[str, Any]:
    """Look up actual values for a dimension (fuzzy search). Use before filtering."""
    allowed = allowed_dimensions(user_id(ctx), access_cfg(ctx))
    if not is_dimension_allowed(dimension, allowed):
        return tool_error(f"Dimension '{dimension}' not found.", "DIMENSION_NOT_FOUND")
    result = ctx.deps.lookup_dimension_values(dimension, search)
    values = result.get("values", [])
    if values is None:
        return tool_error(f"Dimension '{dimension}' not found.", "DIMENSION_NOT_FOUND")
    if not values:
        suffix = f" matching '{search}'" if search else ""
        return tool_error(f"No values found for '{dimension}'{suffix}.", "NO_VALUES_FOUND")
    return values[:100]


def _matches_concept(item: dict, concept: str) -> bool:
    """Fuzzy match concept against catalog metadata without overmatching."""
    c = (concept or "").lower().strip()
    if not c:
        return False

    # Normalize to avoid punctuation/plural edge cases while keeping logic simple.
    concept_tokens = _tokenize_concept(c)
    if not concept_tokens:
        return False

    candidates = [
        item.get("name") or "",
        item.get("display_name") or "",
        item.get("description") or "",
        *[str(s) for s in (item.get("synonyms") or [])],
    ]

    for raw in candidates:
        t = str(raw).lower().strip()
        if not t:
            continue
        # Bidirectional substring allows "total revenue" -> "revenue"
        # while still requiring lexical overlap.
        if c in t or t in c:
            return True
        target_tokens = _tokenize_concept(t)
        # Require all meaningful concept tokens to be present in the target.
        if concept_tokens.issubset(target_tokens):
            return True
    return False


_CONCEPT_STOPWORDS = {
    "a",
    "an",
    "all",
    "any",
    "for",
    "in",
    "of",
    "the",
    "to",
    "total",
}


def _tokenize_concept(text: str) -> set[str]:
    """Tokenize concept text into meaningful lowercase terms."""
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {tok for tok in tokens if tok and tok not in _CONCEPT_STOPWORDS}


@data_tools.tool
def disambiguate(
    ctx: RunContext[DataAgent],
    entity_type: str,
    concept: str,
) -> dict[str, Any]:
    """Find metrics or dimensions matching a concept (name or synonym)."""
    et = (entity_type or "").strip().lower()
    c = (concept or "").strip()
    if not c:
        return tool_error("Concept cannot be empty.", "INVALID_CONCEPT")
    if et not in ("metric", "dimension"):
        return tool_error(
            f"entity_type must be 'metric' or 'dimension', got '{entity_type}'.",
            "INVALID_ENTITY_TYPE",
        )

    catalog = list_catalog(ctx, entity_type=et)
    if isinstance(catalog, dict) and catalog.get("ok") is False:
        return catalog
    items = catalog.get("metrics", []) if et == "metric" else catalog.get("dimensions", [])

    matches = [
        {
            "name": m.get("name"),
            "display_name": m.get("display_name") or m.get("name"),
            "description": (m.get("description") or "").strip() or None,
        }
        for m in items
        if _matches_concept(m, c)
    ]
    if not matches:
        return tool_error(f"No {et}s found for '{concept}'.", "NO_MATCHES")
    return {"matches": matches}


@data_tools.tool(sequential=True)
def query_metric(
    ctx: RunContext[DataAgent],
    metrics: list[str],
    group_by: list[str] | None = None,
    time_grain: str | None = None,
    filters: list[dict[str, Any]] | None = None,
    order: str | None = None,
    limit: int | None = None,
    compare_period: str | None = None,
    include_share: bool = False,
) -> dict[str, Any]:
    """Query one or more metrics with optional filtering/grouping."""
    allowed_m = allowed_metrics(user_id(ctx), access_cfg(ctx))
    allowed_d = allowed_dimensions(user_id(ctx), access_cfg(ctx))

    for m in metrics:
        if not is_metric_allowed(m, allowed_m):
            return tool_error(
                f"Metric '{m}' is not available. Use list_catalog to see available metrics.",
                "METRIC_NOT_ALLOWED",
            )
    for d in group_by or []:
        if not is_dimension_allowed(d, allowed_d):
            return tool_error(
                f"Dimension '{d}' is not available. Use list_catalog to see available dimensions.",
                "DIMENSION_NOT_ALLOWED",
            )
    for f in filters or []:
        field_name = f.get("field") or f.get("dimension")
        if field_name and not is_dimension_allowed(field_name, allowed_d):
            return tool_error(
                f"Dimension '{field_name}' is not available for filtering.",
                "FILTER_DIMENSION_NOT_ALLOWED",
            )

    state = get_runtime_state(ctx)
    result = execute_query_metric(
        core=ctx.deps,
        metrics=metrics,
        dimensions=group_by,
        filters=filters,
        order_by=order,
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

    state.last_query_data = result.data
    state.last_query_metric = result.metrics or metrics
    if not compare_period:
        state.last_query_params = {
            "metrics": metrics,
            "group_by": group_by,
            "filters": filters,
            "order": order,
            "limit": limit,
            "time_grain": time_grain,
        }
    else:
        state.last_query_params = None
    save_runtime_state(ctx, state)

    payload: dict[str, Any] = {"ok": True, "data": result.data, "rows": result.rows}
    if result.period:
        payload["period"] = result.period
    if result.sql:
        payload["sql"] = result.sql
    return payload


def _cleanup_exports(max_files: int = 200, max_age_days: int = 14) -> None:
    """Bound export directory growth by file count and age."""
    export_dir = Path.cwd() / "exports"
    if not export_dir.exists():
        return
    now = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60
    files = [p for p in export_dir.rglob("*") if p.is_file()]
    for p in files:
        try:
            if now - p.stat().st_mtime > max_age_seconds:
                p.unlink(missing_ok=True)
        except Exception:
            continue
    files = [p for p in export_dir.rglob("*") if p.is_file()]
    if len(files) <= max_files:
        return
    files.sort(key=lambda p: p.stat().st_mtime)
    for p in files[: len(files) - max_files]:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            continue


@data_tools.tool(sequential=True)
def export(ctx: RunContext[DataAgent], format: str = "csv") -> str | dict[str, Any]:
    """Export the last query result. format: csv | excel | sheets."""
    state = get_runtime_state(ctx)
    if not state.last_query_data:
        return tool_error("No data to export. Run query_metric first.", "NO_EXPORT_DATA")
    _cleanup_exports()
    fmt = (format or "csv").strip().lower()
    if fmt == "csv":
        try:
            import csv
            from datetime import datetime

            export_dir = Path.cwd() / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = export_dir / f"export_{ts}.csv"
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(state.last_query_data[0].keys()))
                writer.writeheader()
                writer.writerows(state.last_query_data)
            state.pending_files.append({"path": str(path), "title": path.name})
            save_runtime_state(ctx, state)
            return f"Exported {len(state.last_query_data)} rows to {path}"
        except Exception as e:
            return tool_error(f"Export failed: {e}", "EXPORT_FAILED")
    if fmt == "excel":
        try:
            from datetime import datetime

            import pandas as pd

            export_dir = Path.cwd() / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = export_dir / f"export_{ts}.xlsx"
            df = pd.DataFrame(state.last_query_data)
            df.to_excel(path, index=False)
            state.pending_files.append({"path": str(path), "title": path.name})
            save_runtime_state(ctx, state)
            return f"Exported {len(state.last_query_data)} rows to {path}"
        except ImportError:
            return tool_error(
                "Excel export requires openpyxl. Install with: uv sync", "MISSING_DEPENDENCY"
            )
        except Exception as e:
            return tool_error(f"Export failed: {e}", "EXPORT_FAILED")
    if fmt == "sheets":
        return tool_error(
            "Google Sheets export requires additional setup. Use export(format='csv') or "
            "export(format='excel') for now.",
            "NOT_IMPLEMENTED",
        )
    return tool_error(
        f"Unknown format '{format}'. Use csv, excel, or sheets.", "INVALID_EXPORT_FORMAT"
    )


@data_tools.tool(sequential=True)
def generate_chart(ctx: RunContext[DataAgent]) -> str | dict[str, Any]:
    """Generate a chart from the last query result using BSL's auto-detection."""
    state = get_runtime_state(ctx)
    if not state.last_query_data or not state.last_query_metric:
        return tool_error("No data to chart. Run query_metric first.", "NO_CHART_DATA")
    if not state.last_query_params:
        return tool_error(
            "No BSL aggregate available. Run query_metric with group_by first.", "NO_AGGREGATE"
        )
    _cleanup_exports()

    params = state.last_query_params
    result = execute_query_metric(
        core=ctx.deps,
        metrics=params.get("metrics") or [],
        dimensions=params.get("group_by"),
        filters=params.get("filters"),
        order_by=params.get("order"),
        limit=params.get("limit"),
        time_grain=params.get("time_grain"),
    )
    if not result.ok or not result.aggregate:
        return tool_error(
            "No BSL aggregate available. Run query_metric with group_by first.", "NO_AGGREGATE"
        )

    try:
        from datetime import datetime

        chart_bytes = result.aggregate.chart(backend="plotly", format="png")
        if not chart_bytes:
            return tool_error(
                "No dimension to chart. Run query_metric with group_by first.",
                "NO_DIMENSION_FOR_CHART",
            )

        export_dir = Path.cwd() / "exports" / "charts"
        export_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        metric_ref = state.last_query_metric
        display_metric = metric_ref[0] if isinstance(metric_ref, list) else metric_ref
        path = export_dir / f"{display_metric}_{ts}.png"
        path.write_bytes(chart_bytes)

        state.pending_files.append({"path": str(path), "title": path.name})
        save_runtime_state(ctx, state)

        if ctx.metadata and ctx.metadata.get("interface") == "slack":
            return f"Here's your chart for {display_metric}."
        return f"Chart saved to {path}"
    except Exception as e:
        return tool_error(f"Chart generation failed: {e}", "CHART_FAILED")


def readiness_probe(core: DataAgent) -> dict[str, Any]:
    """Build a lightweight readiness payload for health endpoints."""
    checks: dict[str, Any] = {"data_agent_initialized": bool(core)}

    model_count = len(core.bsl_models or {})
    checks["semantic_models_loaded"] = model_count > 0
    checks["semantic_model_count"] = model_count

    warehouse_ok = False
    warehouse_error: str | None = None
    try:
        con = core.ibis_connection
        if hasattr(con, "list_tables"):
            con.list_tables()
        elif hasattr(con, "list_databases"):
            con.list_databases()
        warehouse_ok = True
    except Exception as exc:
        warehouse_error = str(exc)

    checks["warehouse_connection_ok"] = warehouse_ok
    if warehouse_error:
        checks["warehouse_error"] = warehouse_error

    checks["ready"] = all(
        [
            checks["data_agent_initialized"],
            checks["semantic_models_loaded"],
            checks["warehouse_connection_ok"],
        ]
    )
    return checks

"""Core data-agent: BSL model loading + metadata extraction.

``DataAgent`` loads BSL semantic models from YAML, connects to the warehouse,
and provides metric/dimension discovery.  It has **no** LLM logic — that lives
in ``llm.py``.

Typical usage::

    core = DataAgent()
    core.list_metrics()
    core.list_dimensions()
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from boring_semantic_layer import from_config

from falk.settings import Settings, load_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Metadata dataclass — everything BSL doesn't expose from the YAML
# ---------------------------------------------------------------------------

@dataclass
class SemanticMetadata:
    """Metadata extracted from ``semantic_models.yaml`` that BSL strips out.

    BSL's ``from_config`` only keeps the query engine (table, expr, type).
    Everything else — descriptions, display names, synonyms, gotchas — we
    store here so the prompt builder and tools can use it.
    """

    model_descriptions: dict[str, str] = field(default_factory=dict)
    dimension_descriptions: dict[tuple[str, str], str] = field(default_factory=dict)
    dimension_display_names: dict[tuple[str, str], str] = field(default_factory=dict)
    dimension_domains: dict[tuple[str, str], str] = field(default_factory=dict)
    metric_synonyms: dict[str, list[str]] = field(default_factory=dict)
    dimension_synonyms: dict[str, list[str]] = field(default_factory=dict)
    metric_gotchas: dict[str, str] = field(default_factory=dict)
    dimension_gotchas: dict[str, str] = field(default_factory=dict)
    metrics: list[dict[str, Any]] = field(default_factory=list)
    dimensions: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _discover_tables(con: Any) -> dict[str, Any]:
    """Build ``{table_name: ibis_table}`` from all schemas/databases."""
    tables: dict[str, Any] = {}
    skip = {"information_schema", "pg_catalog", "system"}

    try:
        schemas = con.list_databases()
    except Exception:
        schemas = []

    if schemas:
        for schema in schemas:
            if schema in skip:
                continue
            try:
                for t in con.list_tables(database=schema):
                    if t not in tables:
                        tables[t] = con.table(t, database=schema)
            except Exception:
                continue
    else:
        try:
            for t in con.list_tables():
                if t not in tables:
                    tables[t] = con.table(t)
        except Exception:
            pass

    return tables


def _parse_yaml(path: Path) -> dict[str, dict[str, Any]]:
    """Read ``semantic_models.yaml`` and convert list format → dict format.

    BSL's ``from_config`` expects ``{model_name: {table, dimensions: {}, measures: {}}}``
    but our YAML uses a friendlier list format. This function bridges the gap.

    Returns:
        ``model_configs`` dict keyed by model name.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Semantic models config not found: {path}\n"
            "Run 'falk init' to scaffold a project."
        )

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    if "semantic_models" not in raw or not isinstance(raw["semantic_models"], list):
        raise ValueError(
            "Expected 'semantic_models' key with a list of models.\n"
            "Format: semantic_models: [{name: ..., table: ..., dimensions: [...], measures: [...]}]"
        )

    configs: dict[str, dict[str, Any]] = {}
    for entry in raw["semantic_models"]:
        if not isinstance(entry, dict) or "name" not in entry:
            continue

        name = entry["name"]
        cfg = {k: v for k, v in entry.items() if k != "name"}

        # Convert dimensions/measures from list → dict (BSL requirement)
        for key in ("dimensions", "measures"):
            if key in cfg and isinstance(cfg[key], list):
                cfg[key] = {
                    item["name"]: {k: v for k, v in item.items() if k != "name"}
                    for item in cfg[key]
                    if isinstance(item, dict) and "name" in item
                }

        configs[name] = cfg

    return configs


def _humanize(name: str) -> str:
    """Turn ``average_order_value`` into ``Average Order Value``."""
    return name.replace("_", " ").strip().title()


def _extract_metadata(
    model_configs: dict[str, dict[str, Any]],
    loaded_models: set[str],
) -> SemanticMetadata:
    """Extract all metadata from model configs that BSL doesn't keep.

    Iterates the raw YAML configs (already converted to dict format) and
    collects descriptions, display names, synonyms, gotchas, and builds
    flat metrics/dimensions lists.
    """
    meta = SemanticMetadata()

    # Use dicts for natural dedup by name
    metrics_by_name: dict[str, dict[str, Any]] = {}
    dims_by_name: dict[str, dict[str, Any]] = {}

    for model_name, cfg in model_configs.items():
        if model_name not in loaded_models:
            continue

        # Model description
        desc = str(cfg.get("description") or "").strip()
        if desc:
            meta.model_descriptions[model_name] = desc

        # Dimensions
        for dim_name, dim_cfg in (cfg.get("dimensions") or {}).items():
            if not isinstance(dim_cfg, dict):
                continue

            key = (model_name, dim_name)
            d = str(dim_cfg.get("description") or "").strip()
            if d:
                meta.dimension_descriptions[key] = d
            dn = str(dim_cfg.get("display_name") or "").strip()
            if dn:
                meta.dimension_display_names[key] = dn
            dom = str(dim_cfg.get("data_domain") or "").strip()
            if dom:
                meta.dimension_domains[key] = dom
            syns = dim_cfg.get("synonyms") or []
            if syns:
                meta.dimension_synonyms.setdefault(dim_name, [str(s) for s in syns])
            gotcha = str(dim_cfg.get("gotchas") or "").strip()
            if gotcha:
                meta.dimension_gotchas.setdefault(dim_name, gotcha)

            # Build flat dimensions list (first occurrence wins)
            if dim_name not in dims_by_name:
                dims_by_name[dim_name] = {
                    "name": dim_name,
                    "display_name": dn or _humanize(dim_name),
                    "description": d,
                    "synonyms": [str(s) for s in syns],
                    "gotcha": gotcha or None,
                }

        # Measures
        for measure_name, measure_cfg in (cfg.get("measures") or {}).items():
            if not isinstance(measure_cfg, dict):
                continue

            syns = measure_cfg.get("synonyms") or []
            if syns:
                meta.metric_synonyms.setdefault(measure_name, [str(s) for s in syns])
            gotcha = str(measure_cfg.get("gotchas") or "").strip()
            if gotcha:
                meta.metric_gotchas.setdefault(measure_name, gotcha)

            # Build flat metrics list (first occurrence wins)
            if measure_name not in metrics_by_name:
                d = str(measure_cfg.get("description") or "").strip()
                dn = str(measure_cfg.get("display_name") or "").strip()
                metrics_by_name[measure_name] = {
                    "name": measure_name,
                    "display_name": dn or _humanize(measure_name),
                    "description": d,
                    "synonyms": [str(s) for s in syns],
                    "gotcha": gotcha or None,
                }

    meta.metrics = list(metrics_by_name.values())
    meta.dimensions = list(dims_by_name.values())
    return meta


def _load_bsl(
    bsl_models_path: Path,
    connection: dict[str, Any],
) -> tuple[dict[str, Any], SemanticMetadata, Any]:
    """Load BSL models + extract metadata from YAML.

    Returns:
        ``(bsl_models, metadata, ibis_connection)``
    """
    from boring_semantic_layer.profile import get_connection, ProfileError

    try:
        con = get_connection(profile=connection)
    except ProfileError as e:
        logger.error("Failed to connect: %s", e)
        raise

    tables = _discover_tables(con)
    logger.info("Discovered %d tables", len(tables))

    model_configs = _parse_yaml(bsl_models_path)

    # Load each model individually so we can skip those whose tables don't exist
    models: dict[str, Any] = {}
    for name, cfg in model_configs.items():
        try:
            models.update(from_config({name: cfg}, tables=tables))
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping model '%s': %s", name, exc)

    metadata = _extract_metadata(model_configs, set(models.keys()))

    logger.info(
        "Loaded %d / %d BSL models from %s (%d metrics, %d dimensions)",
        len(models),
        len(model_configs),
        bsl_models_path.name,
        len(metadata.metrics),
        len(metadata.dimensions),
    )

    return models, metadata, con


# ---------------------------------------------------------------------------
# DataAgent
# ---------------------------------------------------------------------------

class DataAgent:
    """Core data agent — loads BSL models and provides metric/dimension discovery.

    No LLM logic. The Pydantic AI agent in ``llm.py`` wraps this for
    conversational use.
    """

    def __init__(
        self,
        *,
        bsl_models_path: Path | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        path = (
            Path(bsl_models_path).resolve()
            if bsl_models_path
            else self._settings.bsl_models_path
        )
        self._bsl_models, self._metadata, self._ibis_con = _load_bsl(
            path, self._settings.connection,
        )

    # --- Core properties ------------------------------------------------------

    @property
    def bsl_models(self) -> dict[str, Any]:
        """BSL SemanticModel objects keyed by model name."""
        return self._bsl_models

    @property
    def metadata(self) -> SemanticMetadata:
        """All metadata extracted from the YAML (descriptions, synonyms, etc.)."""
        return self._metadata

    @property
    def ibis_connection(self) -> Any:
        """The ibis database connection."""
        return self._ibis_con

    # --- Convenience aliases for backward compat with prompt builder ----------
    # These let callers do core.model_descriptions instead of core.metadata.model_descriptions

    @property
    def model_descriptions(self) -> dict[str, str]:
        return self._metadata.model_descriptions

    @property
    def dimension_descriptions(self) -> dict[tuple[str, str], str]:
        return self._metadata.dimension_descriptions

    @property
    def dimension_display_names(self) -> dict[tuple[str, str], str]:
        return self._metadata.dimension_display_names

    @property
    def metric_synonyms(self) -> dict[str, list[str]]:
        return self._metadata.metric_synonyms

    @property
    def dimension_synonyms(self) -> dict[str, list[str]]:
        return self._metadata.dimension_synonyms

    @property
    def metric_gotchas(self) -> dict[str, str]:
        return self._metadata.metric_gotchas

    @property
    def dimension_gotchas(self) -> dict[str, str]:
        return self._metadata.dimension_gotchas

    # --- Discovery tools ------------------------------------------------------

    def list_metrics(self) -> dict[str, Any]:
        """All metrics from the semantic model YAML."""
        return {"metrics": self._metadata.metrics}

    def list_dimensions(self) -> dict[str, Any]:
        """All dimensions from the semantic model YAML."""
        return {"dimensions": self._metadata.dimensions}

    def describe_metric(self, name: str) -> str:
        """Get full description of a metric including dimensions and time grains."""
        # First check our metadata for the description
        metric_desc = None
        metric_display = name
        for m in self._metadata.metrics:
            if m["name"] == name:
                metric_desc = m.get("description")
                metric_display = m.get("display_name", name)
                break
        
        if not metric_desc:
            # Try to find which model contains this metric
            for model_name, model in self._bsl_models.items():
                measures = model.measures if hasattr(model, "measures") else []
                if name in measures:
                    dims = [d.name for d in model.get_dimensions().values()] if hasattr(model, "get_dimensions") else []
                    dims_str = ", ".join(dims) if dims else "none"
                    return f"**{metric_display}** — Metric from {model_name}. Dimensions: {dims_str}. Time grains: day, week, month."
            
            return f"Metric '{name}' not found. Use list_metrics to see available metrics."
        
        # Get dimensions and time grains from the model
        from falk.tools.semantic import get_semantic_model_info
        info = get_semantic_model_info(self._bsl_models, name, self._metadata.model_descriptions)
        if info:
            dims = ", ".join(d.name for d in info.dimensions) if info.dimensions else "none"
            grains = ", ".join(info.time_grains) if info.time_grains else "day, week, month"
        else:
            dims = "none"
            grains = "day, week, month"
        
        return f"**{metric_display}** — {metric_desc}. Dimensions: {dims}. Time grains: {grains}."

    def describe_model(self, name: str) -> dict[str, Any] | str:
        """Get full description of a semantic model."""
        from falk.tools.semantic import get_semantic_model_info

        info = get_semantic_model_info(self._bsl_models, name, self._metadata.model_descriptions)
        if not info:
            return f"Model '{name}' not found. Use list_metrics to see available models."

        return {
            "name": name,
            "description": info.description,
            "dimensions": [{"name": d.name, "type": d.type, "description": d.description} for d in info.dimensions],
            "metrics": info.metrics,
            "time_grains": info.time_grains,
        }

    def describe_dimension(self, name: str) -> str:
        """Get full description of a dimension."""
        # Look up from the pre-built list first (YAML-based)
        for dim in self._metadata.dimensions:
            if dim["name"] == name:
                display = dim["display_name"]
                lead = f"**{display}** (`{name}`)" if display != name else f"**{display}**"
                if dim["description"]:
                    lead += f" — {dim['description']}"
                return lead

        return f"Dimension '{name}' not found. Use list_dimensions to see available dimensions."

    def lookup_dimension_values(
        self,
        dimension: str,
        search: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Look up actual values for a dimension from the warehouse."""
        from falk.tools.warehouse import lookup_dimension_values as lookup_fn

        values = lookup_fn(self._bsl_models, dimension, search)
        return {"dimension": dimension, "values": values or []}

"""Core data-agent logic: BSL model loading, metric discovery.

This module provides ``DataAgent``, the central object that loads BSL
semantic models from YAML, connects to DuckDB, and provides metric
discovery.  It is **not** the conversational agent itself — that lives in
``pydantic_agent.py``.

BSL YAML configs are the single source of truth for:
- Which tables to query
- How to aggregate measures
- What dimensions are available
- Descriptions shown in the system prompt and metadata tools

Typical usage (from pydantic_agent or tests)::

    core = DataAgent()
    core.bsl_models         # BSL SemanticModel objects (from YAML)
    core.list_metrics()     # metrics payload (all metrics from BSL models)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from boring_semantic_layer import from_config, from_yaml

from falk.settings import Settings, load_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BSL model loading
# ---------------------------------------------------------------------------

def _discover_tables(con: Any) -> dict[str, Any]:
    """Build ``{table_name: ibis_table}`` from all schemas/databases.

    BSL's ``from_config`` needs a ``tables`` dict to resolve ``table:`` refs
    in the YAML config.  We eagerly load all user tables so BSL can find them.

    Supports DuckDB (list_databases), BigQuery, Snowflake, and other Ibis backends.
    """
    tables: dict[str, Any] = {}
    skip_schemas = {"information_schema", "pg_catalog", "system"}

    # Try multi-schema backends (DuckDB, Snowflake, etc.)
    try:
        schemas = con.list_databases()
    except Exception:
        schemas = []

    if schemas:
        for schema in schemas:
            if schema in skip_schemas:
                continue
            try:
                for tbl_name in con.list_tables(database=schema):
                    if tbl_name not in tables:
                        tables[tbl_name] = con.table(tbl_name, database=schema)
            except Exception:
                continue
    else:
        # Fallback: single schema (e.g. BigQuery, or backend without list_databases)
        try:
            for tbl_name in con.list_tables():
                if tbl_name not in tables:
                    tables[tbl_name] = con.table(tbl_name)
        except Exception:
            pass

    return tables


def _load_bsl_models(
    bsl_models_path: Path,
    connection: dict[str, Any],
) -> tuple[dict[str, Any], Any]:
    """Load BSL semantic models from YAML + database connection.

    Uses inline connection config from falk_project.yaml (passed to BSL get_connection).

    Args:
        bsl_models_path: Path to the BSL YAML config (e.g. ``semantic_models.yaml``).
        connection: Connection dict (e.g. ``{"type": "duckdb", "database": "data/warehouse.duckdb"}``).

    Returns:
        ``(models, model_descriptions, dimension_descriptions, dimension_domains, ibis_connection)``
    """
    from boring_semantic_layer.profile import get_connection, ProfileError

    try:
        con = get_connection(profile=connection)
    except ProfileError as e:
        logger.error("Failed to connect: %s", e)
        raise

    # Discover all tables so BSL can resolve table references
    tables = _discover_tables(con)
    logger.info("Discovered %d tables", len(tables))

    # Load the YAML config and try each model individually so we can skip
    # models whose tables don't exist yet.
    if not bsl_models_path.exists():
        raise FileNotFoundError(
            f"Semantic models config not found: {bsl_models_path}\n"
            "Create semantic_models.yaml in your project root, or run 'falk init' to scaffold."
        )
    raw_config = yaml.safe_load(bsl_models_path.read_text(encoding="utf-8")) or {}
    model_configs = {
        k: v for k, v in raw_config.items()
        if isinstance(v, dict) and k != "profile"
    }

    models: dict[str, Any] = {}
    for model_name, model_cfg in model_configs.items():
        try:
            single = from_config({model_name: model_cfg}, tables=tables)
            models.update(single)
        except (KeyError, ValueError) as exc:
            logger.warning(
                "Skipping model '%s': %s",
                model_name, exc,
            )

    # BSL doesn't pass model-level descriptions through from_config/from_yaml,
    # so we store them separately from the raw YAML.
    model_descriptions: dict[str, str] = {
        name: str(cfg.get("description") or "")
        for name, cfg in model_configs.items()
        if name in models
    }

    # BSL also doesn't pass dimension descriptions through, so we store them
    # separately: {(model_name, dimension_name): description}
    dimension_descriptions: dict[tuple[str, str], str] = {}
    # Display names for business-friendly labels
    # {(model_name, dimension_name): display_name}
    dimension_display_names: dict[tuple[str, str], str] = {}
    # Also store custom metadata like data_domain
    dimension_domains: dict[tuple[str, str], str] = {}
    # Synonyms — optional aliases for metrics and dimensions
    # {entity_name: [synonym1, synonym2, ...]}
    metric_synonyms: dict[str, list[str]] = {}
    dimension_synonyms: dict[str, list[str]] = {}
    # Gotchas — things the agent should warn about
    # {entity_name: gotcha_string}
    metric_gotchas: dict[str, str] = {}
    dimension_gotchas: dict[str, str] = {}

    for model_name, model_cfg in model_configs.items():
        if model_name not in models:
            continue

        # Dimension metadata
        dims_cfg = model_cfg.get("dimensions") or {}
        for dim_name, dim_cfg in dims_cfg.items():
            if isinstance(dim_cfg, dict):
                desc = str(dim_cfg.get("description") or "")
                if desc:
                    dimension_descriptions[(model_name, dim_name)] = desc
                display_name = str(dim_cfg.get("display_name") or "").strip()
                if display_name:
                    dimension_display_names[(model_name, dim_name)] = display_name
                domain = str(dim_cfg.get("data_domain") or "").strip()
                if domain:
                    dimension_domains[(model_name, dim_name)] = domain
                syns = dim_cfg.get("synonyms") or []
                if syns and dim_name not in dimension_synonyms:
                    dimension_synonyms[dim_name] = [str(s) for s in syns]
                gotcha = str(dim_cfg.get("gotchas") or "").strip()
                if gotcha and dim_name not in dimension_gotchas:
                    dimension_gotchas[dim_name] = gotcha

        # Measure synonyms + gotchas
        measures_cfg = model_cfg.get("measures") or {}
        for measure_name, measure_cfg in measures_cfg.items():
            if isinstance(measure_cfg, dict):
                syns = measure_cfg.get("synonyms") or []
                if syns and measure_name not in metric_synonyms:
                    metric_synonyms[measure_name] = [str(s) for s in syns]
                gotcha = str(measure_cfg.get("gotchas") or "").strip()
                if gotcha and measure_name not in metric_gotchas:
                    metric_gotchas[measure_name] = gotcha

    logger.info(
        "Loaded %d / %d BSL models from %s (%d metric synonyms, %d dimension synonyms, %d gotchas)",
        len(models),
        len(model_configs),
        bsl_models_path.name,
        len(metric_synonyms),
        len(dimension_synonyms),
        len(metric_gotchas) + len(dimension_gotchas),
    )

    return (
        models,
        model_descriptions,
        dimension_descriptions,
        dimension_display_names,
        dimension_domains,
        metric_synonyms,
        dimension_synonyms,
        metric_gotchas,
        dimension_gotchas,
        con,
    )


# ---------------------------------------------------------------------------
# DataAgent
# ---------------------------------------------------------------------------

class DataAgent:
    """Minimal, embeddable data-agent core.

    Responsibilities:

    - Load BSL semantic models from YAML config (the query engine)
    - Connect to DuckDB warehouse
    - Provide ``list_metrics()`` (all metrics from loaded BSL models)

    This class intentionally has **no** LLM/planner logic.  The Pydantic AI
    agent in ``pydantic_agent.py`` wraps it for conversational use.
    """

    def __init__(
        self,
        *,
        bsl_models_path: Path | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or load_settings()

        _bsl_path = (
            Path(bsl_models_path).resolve()
            if bsl_models_path
            else self._settings.bsl_models_path
        )

        (
            self._bsl_models,
            self._model_descriptions,
            self._dimension_descriptions,
            self._dimension_display_names,
            self._dimension_domains,
            self._metric_synonyms,
            self._dimension_synonyms,
            self._metric_gotchas,
            self._dimension_gotchas,
            self._ibis_con,
        ) = _load_bsl_models(
            bsl_models_path=_bsl_path,
            connection=self._settings.connection,
        )

    # --- public ---------------------------------------------------------------

    @property
    def bsl_models(self) -> dict[str, Any]:
        """BSL SemanticModel objects keyed by model name."""
        return self._bsl_models

    @property
    def model_descriptions(self) -> dict[str, str]:
        """Model-level descriptions from the BSL YAML (keyed by model name).

        BSL's ``from_config`` doesn't pass descriptions to the SemanticModel
        object, so we store them separately from the raw YAML.
        """
        return self._model_descriptions

    @property
    def dimension_descriptions(self) -> dict[tuple[str, str], str]:
        """Dimension descriptions from the BSL YAML.

        Keyed by ``(model_name, dimension_name)`` tuples.
        BSL doesn't pass dimension descriptions through, so we store them separately.
        """
        return self._dimension_descriptions

    @property
    def dimension_display_names(self) -> dict[tuple[str, str], str]:
        """Business-friendly display names for dimensions.

        Keyed by ``(model_name, dimension_name)`` tuples.
        Example: ``{("sales_metrics", "customer_segment"): "Customer Segment"}``
        Falls back to snake_case name if not specified.
        """
        return self._dimension_display_names

    @property
    def dimension_domains(self) -> dict[tuple[str, str], str]:
        """Dimension data domains from the BSL YAML (e.g., "core", "affiliate", "finance").

        Keyed by ``(model_name, dimension_name)`` tuples.
        Custom metadata field — BSL ignores it, so we store it separately.
        """
        return self._dimension_domains

    @property
    def metric_synonyms(self) -> dict[str, list[str]]:
        """Metric synonyms from the BSL YAML.

        Keyed by metric name, value is a list of synonyms.
        Example: ``{"revenue": ["sales", "income", "turnover"]}``
        """
        return self._metric_synonyms

    @property
    def dimension_synonyms(self) -> dict[str, list[str]]:
        """Dimension synonyms from the BSL YAML.

        Keyed by dimension name, value is a list of synonyms.
        Example: ``{"region": ["territory", "area", "market"]}``
        """
        return self._dimension_synonyms

    @property
    def metric_gotchas(self) -> dict[str, str]:
        """Metric gotchas from the BSL YAML.

        Keyed by metric name, value is the gotcha text.
        Example: ``{"revenue": "Revenue has a 48-hour reporting delay"}``
        """
        return self._metric_gotchas

    @property
    def dimension_gotchas(self) -> dict[str, str]:
        """Dimension gotchas from the BSL YAML.

        Keyed by dimension name, value is the gotcha text.
        Example: ``{"region": "LATAM data only available from 2025-06 onwards"}``
        """
        return self._dimension_gotchas

    @property
    def ibis_connection(self) -> Any:
        """The ibis DuckDB connection (shared across queries)."""
        return self._ibis_con

    def list_metrics(self) -> dict[str, Any]:
        """List available measures grouped by semantic model.

        Returns all metrics from all loaded BSL models.
        Returns ``{"ok": True, "semantic_models": { ... }}``.
        """
        out: dict[str, list[dict[str, Any]]] = {}

        for model_name, model in self._bsl_models.items():
            measures: list[dict[str, Any]] = []
            for name, measure in model.get_measures().items():
                measures.append({
                    "name": name,
                    "label": name,
                    "description": measure.description or "",
                })
            if measures:
                out[model_name] = measures

        return {"ok": True, "semantic_models": out}

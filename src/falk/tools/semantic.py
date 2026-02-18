"""Semantic-model info lookups — reads from BSL models (single source of truth).

Provides ``get_semantic_model_info`` which returns structured information about
a semantic model or metric, including dimensions, time grains, and descriptions.
Used by the ``describe_metric`` tool in ``pydantic_agent.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DimensionInfo:
    name: str
    label: str
    description: str
    type: str


@dataclass(frozen=True)
class SemanticModelInfo:
    description: str
    dimensions: list[DimensionInfo]
    metrics: list[str]
    time_grains: list[str]


def get_semantic_model_info(
    bsl_models: dict[str, Any],
    name: str,
    model_descriptions: dict[str, str] | None = None,
) -> SemanticModelInfo | None:
    """Look up a semantic model OR measure (metric) by name.

    Args:
        bsl_models: BSL SemanticModel objects keyed by model name.
        name: Model name or measure name to look up.
        model_descriptions: Optional model-level descriptions from YAML.

    Returns:
        ``SemanticModelInfo`` or ``None`` if not found.
    """
    name_l = name.strip().lower()
    if not name_l:
        return None

    model_descriptions = model_descriptions or {}

    # Direct model match
    for model_name, model in bsl_models.items():
        if model_name.lower() == name_l:
            return _info_from_bsl_model(model, model_descriptions.get(model_name))

    # Measure match — search all models
    for model_name, model in bsl_models.items():
        measures = model.measures if hasattr(model, "measures") else list(model.get("measures", {}).keys())
        if name_l in [m.lower() for m in measures]:
            # Found the metric in this model
            info = _info_from_bsl_model(model, model_descriptions.get(model_name))
            # Get the actual measure name (preserve case)
            actual_name = next((m for m in measures if m.lower() == name_l), name)
            return SemanticModelInfo(
                description=f"Metric: {actual_name}",  # BSL doesn't expose measure descriptions reliably
                dimensions=info.dimensions,
                metrics=[actual_name],
                time_grains=info.time_grains,
            )

    return None


def _info_from_bsl_model(model: Any, description: str | None = None) -> SemanticModelInfo:
    """Extract structured info from a BSL SemanticModel."""
    dims: list[DimensionInfo] = []
    time_grains: set[str] = set()

    for dim_name, dim in model.get_dimensions().items():
        dims.append(
            DimensionInfo(
                name=dim_name,
                label=dim_name,
                description=dim.description or "",
                type="time" if dim.is_time_dimension else "categorical",
            )
        )
        if dim.is_time_dimension:
            time_grains.update({"day", "week", "month"})

    metrics = list(model.measures) if hasattr(model, "measures") else list(model.get("measures", {}).keys())

    if not time_grains:
        time_grains = {"day", "week", "month"}

    return SemanticModelInfo(
        description=description or model.description or "",
        dimensions=dims,
        metrics=metrics,
        time_grains=sorted(time_grains),
    )

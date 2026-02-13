"""System-prompt construction for the data agent.

This module owns the SYSTEM_PROMPT_TEMPLATE and every helper that turns BSL
semantic model metadata + the user's ``falk_project.yaml`` into the final
prompt string.

Everything that is business-specific lives in ``falk_project.yaml``.
The built-in template is intentionally **generic** so it works out-of-the-box
for any set of BSL models.  Users of the library extend it via YAML — they
never need to edit this file.

Extension points
-----------------
``semantic_models.yaml``
  ``synonyms`` on metrics/dimensions — auto-injected into the prompt

``falk_project.yaml``
  ``business.description``  — company / domain context paragraph
  ``examples``              — custom query examples (appended to auto-generated ones)
  ``welcome``               — override the first-message suggestions
  ``rules``                 — business rules the agent must follow
  ``response_rules``        — additional response-style rules
  ``custom_sections``       — freeform titled sections appended to the prompt

``build_system_prompt()`` is the only function the rest of the codebase calls.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Template — intentionally generic (no partner, no clicks)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """\
You are a data assistant that helps teams explore their data using semantic models.{database_info}

Today is {current_date} ({day_of_week}).

{company_context}
{business_context}

## Your Tools

- `list_metrics()` — see available metrics
- `list_dimensions()` — see available dimensions
- `describe_metric(name)` — get metric details
- `describe_model(name)` — get full description of a semantic model
- `describe_dimension(name)` — get full description of a dimension
- `lookup_values(dimension, search)` — find actual values in a dimension (fuzzy)
- `query_metric(metric, group_by, time_grain, filters, order, limit)` — query data
- `compare_periods(metric, period, group_by, limit)` — compare this vs last week/month/quarter
- `decompose_metric(metric, period, dimensions?)` — explain why a metric changed (root cause). Pass dimensions only if user specified; omit to analyze all.
- `compute_share()` — show % breakdown from the last query
- `export_to_csv()` — export last result to CSV
- `export_to_excel()` — export last result to Excel (.xlsx)
- `export_to_google_sheets()` — export last result to Google Sheets
- `generate_chart(chart_type, dimension)` — generate a Plotly chart
  - If chart_type is omitted, auto-detects: line (time series), pie (2-8 categories), bar (9+)
  - In Slack the chart is uploaded; in web UI the tool returns the file path

## How to Query Data

1. Pick the metric (use `list_metrics` if unsure)
2. If user mentions a specific entity, use `lookup_values` to find exact value
3. Call `query_metric` with the right parameters

{examples}

## Disambiguation

Some concepts map to multiple dimensions. When ambiguous:
- Use `describe_dimension` to check meanings
- Ask the user to clarify

{dimension_glossary}

{vocabulary}

{rules_content}

## Response Formatting

Use clear formatting in responses:
- *Bold* for key terms and emphasis (use asterisks)
- **Always use bullet lists for hierarchical or multi-level data**
  - Top-level: `- Category` or `- Item`
  - Nested/sub-items: `  - Region: value` (2 spaces before -)
  - Example:
    ```
    - Electronics
      - EU: $100
      - US: $200
    - Sports
      - EU: $150
    ```
- Never use • or other bullet chars directly; use `-` and the converter handles it

## First Message

If the user says hello or asks a vague question, welcome them:
{welcome_examples}

{extra_rules}
{gotchas}
{custom_sections}\
"""


# ---------------------------------------------------------------------------
# Database type detection
# ---------------------------------------------------------------------------

def _detect_database_type(bsl_models: dict[str, Any]) -> str | None:
    """Detect database type from BSL models.
    
    BSL uses Ibis which supports:
    athena, bigquery, clickhouse, databricks, datafusion, druid, duckdb,
    exasol, flink, impala, materialize, mssql, mysql, oracle, polars,
    postgres, pyspark, risingwave, singlestoredb, snowflake, sqlite, trino
    
    Returns:
        Database type name (e.g., "snowflake", "bigquery") or None if unknown
    """
    for model in bsl_models.values():
        # Try to get connection info from BSL model
        if hasattr(model, 'connection') and model.connection:
            conn = model.connection
            # Ibis connections have a backend name
            if hasattr(conn, 'name'):
                return conn.name.lower()
            # Check class name as fallback
            conn_type = type(conn).__name__.lower()
            if 'snowflake' in conn_type:
                return 'snowflake'
            elif 'bigquery' in conn_type:
                return 'bigquery'
            elif 'postgres' in conn_type:
                return 'postgres'
            elif 'duckdb' in conn_type:
                return 'duckdb'
            elif 'athena' in conn_type:
                return 'athena'
            elif 'databricks' in conn_type:
                return 'databricks'
    return None


def _build_database_info(bsl_models: dict[str, Any]) -> str:
    """Build database info string for prompt.
    
    Returns empty string or formatted database type info.
    """
    db_type = _detect_database_type(bsl_models)
    if not db_type:
        return ""
    
    # Capitalize for display
    db_display = {
        'bigquery': 'BigQuery',
        'snowflake': 'Snowflake',
        'postgres': 'PostgreSQL',
        'duckdb': 'DuckDB',
        'athena': 'Amazon Athena',
        'databricks': 'Databricks',
        'clickhouse': 'ClickHouse',
        'mssql': 'SQL Server',
        'mysql': 'MySQL',
        'oracle': 'Oracle',
        'redshift': 'Amazon Redshift',
        'trino': 'Trino',
    }.get(db_type, db_type.title())
    
    return f"\nData source: {db_display} warehouse"


def _load_rules_content(project_root: Path | None = None) -> str:
    """Load RULES.md content if it exists.
    
    Args:
        project_root: Project root directory
        
    Returns:
        Formatted rules content or empty string
    """
    if not project_root:
        return ""
    
    rules_file = project_root / "RULES.md"
    if not rules_file.exists():
        return ""
    
    try:
        with open(rules_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            # Remove the title and intro comment if present
            lines = content.split('\n')
            filtered = []
            skip_intro = True
            for line in lines:
                # Skip title and blockquote intro
                if skip_intro:
                    if line.startswith('# ') or line.startswith('> '):
                        continue
                    elif line.strip() == '':
                        continue
                    else:
                        skip_intro = False
                filtered.append(line)
            
            result = '\n'.join(filtered).strip()
            return f"\n{result}\n" if result else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

def build_system_prompt(
    bsl_models: dict[str, Any],
    agent_config: Any = None,
    model_descriptions: dict[str, str] | None = None,
    dimension_descriptions: dict[tuple[str, str], str] | None = None,
    metric_synonyms: dict[str, list[str]] | None = None,
    dimension_synonyms: dict[str, list[str]] | None = None,
    metric_gotchas: dict[str, str] | None = None,
    dimension_gotchas: dict[str, str] | None = None,
    project_root: Path | None = None,
) -> str:
    """Assemble the full system prompt from template + BSL model metadata.

    Args:
        bsl_models: BSL SemanticModel objects keyed by model name.
        agent_config: AgentConfig from falk_project.yaml (optional).
        model_descriptions: Model-level descriptions from YAML (optional).
        dimension_descriptions: Dimension descriptions from YAML (optional).
        metric_synonyms: Metric synonyms from YAML (optional).
        dimension_synonyms: Dimension synonyms from YAML (optional).
        metric_gotchas: Metric gotchas from YAML (optional).
        dimension_gotchas: Dimension gotchas from YAML (optional).
        project_root: Project root for loading RULES.md (optional).
    """
    today = date.today()
    dimension_descriptions = dimension_descriptions or {}
    config = _agent_config_to_dict(agent_config)

    return SYSTEM_PROMPT_TEMPLATE.format(
        current_date=today.isoformat(),
        day_of_week=today.strftime("%A"),
        database_info=_build_database_info(bsl_models),
        company_context=_build_company_context(config),
        business_context=_build_business_context(
            bsl_models, model_descriptions or {}, dimension_descriptions,
        ),
        examples=_build_examples(bsl_models, config),
        dimension_glossary=_build_dimension_glossary(
            bsl_models, dimension_descriptions,
        ),
        vocabulary=_build_vocabulary(metric_synonyms, dimension_synonyms),
        rules_content=_load_rules_content(project_root),
        gotchas=_build_gotchas(
            metric_gotchas, dimension_gotchas, config.get("gotchas"),
        ),
        welcome_examples=_build_welcome(bsl_models, config),
        extra_rules=_build_extra_list(config.get("rules")),
        custom_sections=_build_custom_sections(config),
    )


# ---------------------------------------------------------------------------
# Agent config loader
# ---------------------------------------------------------------------------

def _agent_config_to_dict(agent_config: Any) -> dict[str, Any]:
    """Convert AgentConfig from falk_project.yaml to dict format for prompt building.
    
    Converts the new falk_project.yaml structure to the format expected by
    the prompt building functions.
    """
    if not agent_config:
        return {}
    
    config_dict = {}
    
    # Map AgentConfig fields to old config format
    if hasattr(agent_config, 'context') and agent_config.context:
        config_dict['business'] = {'description': agent_config.context}
    
    if hasattr(agent_config, 'examples') and agent_config.examples:
        config_dict['examples'] = agent_config.examples
    
    if hasattr(agent_config, 'welcome') and agent_config.welcome:
        config_dict['welcome'] = agent_config.welcome
    
    if hasattr(agent_config, 'rules') and agent_config.rules:
        config_dict['rules'] = agent_config.rules
    
    return config_dict


# ---------------------------------------------------------------------------
# Company context
# ---------------------------------------------------------------------------

def _build_company_context(config: dict[str, Any]) -> str:
    business = config.get("business") or {}
    desc = str(business.get("description") or "").strip() if isinstance(business, dict) else ""
    # Fallback: old format had description at top level
    if not desc:
        desc = str(config.get("description") or "").strip()
    return f"## About the Business\n{desc}" if desc else ""


# ---------------------------------------------------------------------------
# Auto-generated examples from BSL models
# ---------------------------------------------------------------------------

def _build_examples(bsl_models: dict[str, Any], config: dict[str, Any]) -> str:
    """Build the Examples section from BSL model metadata + user overrides.

    Auto-generates generic examples using the first metric and dimension
    found in the loaded BSL models, then appends any custom examples from
    ``agent.yaml``.
    """
    # Pick a sample metric and dimension from whatever BSL models are loaded
    sample_metric = None
    sample_dimension = None
    for _model_name, model in bsl_models.items():
        if not sample_metric:
            measures = list(model.get_measures().keys())
            if measures:
                sample_metric = measures[0]
        if not sample_dimension:
            dims = [
                d for d in model.get_dimensions().keys()
                if d != "date"
            ]
            if dims:
                sample_dimension = dims[0]
        if sample_metric and sample_dimension:
            break

    m = sample_metric or "metric_name"
    d = sample_dimension or "dimension_name"

    lines = [
        "Examples:",
        f'- "total {m}" -> query_metric(metric="{m}")',
        f'- "{m} by {d}" -> query_metric(metric="{m}", group_by=["{d}"])',
        f'- "top 10 {d}s by {m}" -> query_metric(metric="{m}", '
        f'group_by=["{d}"], order="desc", limit=10)',
        f'- "{m} for <entity>" -> lookup_values("{d}", "<entity>") -> get exact name -> '
        f'query_metric(metric="{m}", group_by=["{d}"], '
        f'filters=[{{"dimension": "{d}", "op": "=", "value": "<exact>"}}])',
        f'- "{m} by month" -> query_metric(metric="{m}", time_grain="month")',
        f'- "compare {m} this month vs last" -> compare_periods(metric="{m}", period="month")',
        f'- "what % does each {d} have?" -> first query_metric, then compute_share()',
        '- "show me a chart" -> generate_chart() (auto-detects best type)',
        '- "show me a line chart over time" -> generate_chart(chart_type="line")',
        '- "daily breakdown for top 2" -> TWO STEPS REQUIRED:',
        f'  1) query_metric(metric="{m}", group_by=["{d}"], order="desc", limit=2)',
        f'  2) query_metric(metric="{m}", group_by=["{d}", "date"], '
        f'filters=[{{"dimension": "{d}", "op": "IN", "value": ["<top1>", "<top2>"]}}])',
        "  CRITICAL: For 'top N with breakdown', always do step 1 first, "
        "then filter by results in step 2.",
        '- "show me a time breakdown as a chart" -> FIRST run query_metric with the '
        "same filters from the previous query but add time_grain or group_by date, "
        'THEN generate_chart(chart_type="line"). Preserves context from prior query.',
    ]

    # Append domain hints from agent.yaml (natural language, no tool names needed)
    custom = config.get("examples") or []
    if custom:
        lines.append("")
        lines.append("Domain-specific hints (from your team):")
        for ex in custom:
            lines.append(f"- {ex}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Welcome / first-message examples
# ---------------------------------------------------------------------------

def _build_welcome(bsl_models: dict[str, Any], config: dict[str, Any]) -> str:
    """Build the welcome-message examples.

    Uses custom ones from ``agent.yaml`` if provided, otherwise
    auto-generates from BSL model metadata.
    """
    custom = config.get("welcome")
    if custom:
        return "\n".join(f"- {ex}" for ex in custom)

    # Auto-generate from BSL models
    sample_metric = None
    sample_dimension = None
    for _model_name, model in bsl_models.items():
        if not sample_metric:
            measures = list(model.get_measures().keys())
            if measures:
                sample_metric = measures[0]
        if not sample_dimension:
            dims = [d for d in model.get_dimensions().keys() if d != "date"]
            if dims:
                sample_dimension = dims[0]
        if sample_metric and sample_dimension:
            break

    m = sample_metric or "your_metric"
    d = sample_dimension or "dimension"

    return "\n".join([
        f'- "What was our total {m} last week?"',
        f'- "Top 10 {d}s by {m} this month"',
        f'- "Compare {m} this month vs last month"',
        f'- "What % of {m} does each {d} have?"',
        '- "What metrics are available?"',
    ])


# ---------------------------------------------------------------------------
# Extra rules / response rules from YAML
# ---------------------------------------------------------------------------

def _build_extra_list(items: list[str] | None) -> str:
    """Render a list of extra rules/guidelines from agent.yaml."""
    if not items:
        return ""
    return "\n" + "\n".join(f"- {item}" for item in items)


# ---------------------------------------------------------------------------
# Custom freeform sections from YAML
# ---------------------------------------------------------------------------

def _build_custom_sections(config: dict[str, Any]) -> str:
    """Render custom_sections from agent.yaml as prompt sections."""
    sections = config.get("custom_sections") or []
    if not sections:
        return ""

    parts: list[str] = []
    for sec in sections:
        title = sec.get("title", "").strip()
        content = sec.get("content", "").strip()
        if title and content:
            parts.append(f"\n## {title}\n{content}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Vocabulary (synonyms from semantic_models.yaml)
# ---------------------------------------------------------------------------

def _build_vocabulary(
    metric_synonyms: dict[str, list[str]] | None = None,
    dimension_synonyms: dict[str, list[str]] | None = None,
) -> str:
    """Build the vocabulary section from metric/dimension synonyms.

    Tells the LLM what everyday terms map to which metrics/dimensions.
    """
    metric_synonyms = metric_synonyms or {}
    dimension_synonyms = dimension_synonyms or {}

    if not metric_synonyms and not dimension_synonyms:
        return ""

    lines = ["## Vocabulary (your team's terminology)"]
    lines.append("When users say any of these terms, map to the corresponding metric or dimension:")

    for metric, syns in sorted(metric_synonyms.items()):
        quoted = ", ".join(f'"{s}"' for s in syns)
        lines.append(f"- {quoted} -> **{metric}** (metric)")

    for dim, syns in sorted(dimension_synonyms.items()):
        quoted = ", ".join(f'"{s}"' for s in syns)
        lines.append(f"- {quoted} -> **{dim}** (dimension)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gotchas / data quality notes (from semantic_models.yaml + agent.yaml)
# ---------------------------------------------------------------------------

def _build_gotchas(
    metric_gotchas: dict[str, str] | None = None,
    dimension_gotchas: dict[str, str] | None = None,
    global_gotchas: list[str] | None = None,
) -> str:
    """Build the gotchas / data quality notes section.

    Tells the LLM about known data quirks so it can proactively warn users
    or avoid incorrect queries.
    """
    metric_gotchas = metric_gotchas or {}
    dimension_gotchas = dimension_gotchas or {}
    global_gotchas = global_gotchas or []

    if not metric_gotchas and not dimension_gotchas and not global_gotchas:
        return ""

    lines = [
        "## Data Quality Notes (gotchas)",
        "Keep these in mind when querying — mention them to the user when relevant:",
        "**Always run the query first.** Run query_metric (or other tools) to get data, then mention "
        "gotchas in your response. Do not skip querying just because a gotcha applies.",
    ]

    for name, note in sorted(metric_gotchas.items()):
        lines.append(f"- **{name}** (metric): {note}")

    for name, note in sorted(dimension_gotchas.items()):
        lines.append(f"- **{name}** (dimension): {note}")

    for note in global_gotchas:
        lines.append(f"- {note}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Auto-generated business context from BSL models
# ---------------------------------------------------------------------------

def _build_business_context(
    bsl_models: dict[str, Any],
    model_descriptions: dict[str, str] | None = None,
    dimension_descriptions: dict[tuple[str, str], str] | None = None,
) -> str:
    """Auto-generate "Data Models" + "Key Concepts" from BSL models."""
    if not bsl_models:
        return ""

    model_descriptions = model_descriptions or {}
    dimension_descriptions = dimension_descriptions or {}
    sections: list[str] = []

    # ---- Data Models (one-line summaries) ----
    model_lines = ["## Data Models"]
    for name, model in bsl_models.items():
        desc = model_descriptions.get(name) or model.description or ""
        summary = _extract_summary(desc)
        if summary:
            model_lines.append(f"- *{name}* — {summary}")
        else:
            model_lines.append(f"- *{name}*")
    sections.append("\n".join(model_lines))

    # ---- Key Concepts (dimensions shared across 2+ models) ----
    VARIANT_SUFFIXES = ("_code", "_region", "_state", "_id", "_date")

    dim_model_count: dict[str, int] = {}
    dim_info: dict[str, str] = {}  # name -> first_sentence

    for model_name, model in bsl_models.items():
        seen_in_model: set[str] = set()
        for dim_name, dim in model.get_dimensions().items():
            if dim_name in seen_in_model:
                continue
            seen_in_model.add(dim_name)
            dim_model_count[dim_name] = dim_model_count.get(dim_name, 0) + 1
            if dim_name not in dim_info:
                desc = dimension_descriptions.get((model_name, dim_name)) or ""
                dim_info[dim_name] = _first_sentence(desc)

    shared_dims = [
        (n, dim_info[n])
        for n in dim_model_count
        if dim_model_count[n] >= 2
        and n in dim_info
        and n != "date"
        and not any(n.endswith(s) for s in VARIANT_SUFFIXES)
    ]
    shared_dims.sort(key=lambda x: (-dim_model_count[x[0]], x[0]))

    if shared_dims:
        concept_lines = ["## Key Concepts"]
        for dname, desc in shared_dims[:15]:
            if desc:
                concept_lines.append(f"- *{dname}* — {desc}")
            else:
                concept_lines.append(f"- *{dname}*")
        sections.append("\n".join(concept_lines))

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Dimension glossary (disambiguation hints)
# ---------------------------------------------------------------------------

def _build_dimension_glossary(
    bsl_models: dict[str, Any],
    dimension_descriptions: dict[tuple[str, str], str] | None = None,
) -> str:
    """Auto-generate disambiguation hints for ambiguous dimension groups."""
    dimension_descriptions = dimension_descriptions or {}
    seen: set[str] = set()
    all_dims: list[tuple[str, str]] = []  # (name, desc_short)

    for model_name, model in bsl_models.items():
        for dim_name, dim in model.get_dimensions().items():
            if dim_name in seen:
                continue
            seen.add(dim_name)
            desc = dimension_descriptions.get((model_name, dim_name)) or ""
            desc = desc.replace("\r\n", " ").replace("\n", " ").strip()
            dot = desc.find(".")
            if dot > 0:
                desc = desc[:dot + 1]
            all_dims.append((dim_name, desc))

    CONCEPT_GROUPS = [
        (
            "Country / Geography",
            ["country", "geography", "market_intent", "state"],
            "Default to the most common country dimension unless the user "
            "specifically asks about a different geographic concept.",
        ),
        (
            "Partner / Entity",
            ["partner", "vendor", "supplier", "customer"],
            "Default to the base name dimension. Use variant dimensions "
            "(brand, parent, etc.) only when explicitly asked.",
        ),
    ]

    sections: list[str] = []
    for concept_label, keywords, default_hint in CONCEPT_GROUPS:
        matching = [
            (n, d) for n, d in all_dims
            if any(kw in n.lower() for kw in keywords)
        ]
        if len(matching) < 2:
            continue
        lines = [f"### {concept_label}"]
        for dim_name, desc in matching:
            if desc:
                lines.append(f"- `{dim_name}` — {desc}")
            else:
                lines.append(f"- `{dim_name}`")
        lines.append(f"-> {default_hint}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections) if sections else ""


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _extract_summary(description: str) -> str:
    """Extract a clean one-line summary from a model description."""
    lines = description.replace("\r\n", "\n").split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("---") or stripped.startswith("**"):
            continue
        clean = stripped.replace("`", "").replace("**", "").replace("*", "")
        if clean.rstrip(":").strip().lower() in ("description", "purpose", "grain", "notes"):
            continue
        if len(clean) > 150:
            cut = clean[:150].rfind(" ")
            clean = clean[:cut] + "..." if cut > 80 else clean[:150] + "..."
        return clean
    return ""


def _first_sentence(text: str) -> str:
    """Extract first sentence, stripping markdown formatting."""
    clean = text.replace("\r\n", " ").replace("\n", " ").strip()
    clean = clean.replace("`", "").replace("**", "").replace("*", "")
    for end_char in [".", "!"]:
        idx = clean.find(end_char)
        if 10 < idx < 200:
            return clean[:idx + 1]
    if len(clean) > 120:
        cut = clean[:120].rfind(" ")
        return clean[:cut] + "..." if cut > 60 else clean[:120] + "..."
    return clean

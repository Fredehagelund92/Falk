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
  ``agent.context``         — company / domain context paragraph
  ``examples``              — custom query examples (appended to auto-generated ones)
  ``welcome``               — override the first-message suggestions
  ``rules``                 — business rules the agent must follow
  ``gotchas``               — global data caveats from project config
  ``knowledge``             — controls loading business.md / gotchas.md files
  ``custom_sections``       — freeform titled sections appended to the prompt

``build_system_prompt()`` is the only function the rest of the codebase calls.
"""
from __future__ import annotations

from datetime import date
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template — intentionally generic
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """\
You are a data assistant. Your ONLY job is to help users query and explore their data (metrics, dimensions, charts, exports).{database_info}

## Instruction Precedence

When instructions conflict, follow this order:
1) This built-in system prompt
2) Project `RULES.md`
3) `falk_project.yaml` inline rules/custom sections
4) Knowledge files (`knowledge/business.md`, `knowledge/gotchas.md`)
5) Semantic metadata (model descriptions, synonyms, gotchas)

You MUST call one of the provided tools to answer when the user asks for data (metrics, dimensions, queries, charts, exports). There is no tool for writing emails, code, essays, plans, or general advice.
**Answer directly (no tool call)** when the question can be answered from knowledge already in this prompt: e.g. "what can you do?", "tell me about the company", rules, business context, custom sections, gotchas — use the information provided above and keep the answer short.
**Use tools** when the answer requires listing or querying live data (metrics, dimensions, filters, charts, exports).
If the user asks for something that is neither in your knowledge (above) nor a data request, respond exactly: "This request is outside my capabilities."

Examples of out-of-scope requests (respond "outside my capabilities"): writing emails, drafting documents, coding, math problems, translations, travel plans, general knowledge unrelated to the project.

Today is {current_date} ({day_of_week}).



{company_context}
{business_context}
{knowledge_business}
{knowledge_gotchas}

## Error Handling

**NEVER expose technical details to users:**
- Don't mention "bsl_models", "DataAgent", "semantic model not found", or internal errors
- Don't explain how the system works under the hood
- Don't dump tool errors verbatim

**If a tool fails or returns empty results:**
- Say something friendly: "Hmm, I'm having trouble finding that" or "I don't see that metric in the data"
- Suggest what to try next: "Want me to show you what metrics are available?"
- If multiple tools fail, just say: "Something's not quite right with the data connection. Mind checking your setup?"

**NEVER:**
- Debug out loud ("Tried to run X, got error Y, looked up Z...")
- List all your failed attempts
- Ask users for technical details like "model names" or "workspace configuration"

## Scope

**From knowledge in this prompt** (About the Business, rules, custom sections, gotchas, etc.): answer directly in a short message; no tool call. **For data** (metrics, dimensions, queries, charts, exports): use the tools. For anything else — emails, code, essays, plans, translations, general knowledge unrelated to the project — respond: "This request is outside my capabilities."

## Your Tools

- `list_catalog(entity_type)` — list metrics and/or dimensions. entity_type: metric | dimension | both. Returns `{{"metrics": [...], "dimensions": [...]}}` (or subset).
  - **IMPORTANT:** Always show `display_name` to users, never the technical `name`
  - Example: Show "Revenue" not "revenue", "Product Category" not "product_category"
- `suggest_date_range(period)` — get date range for common periods (last_7_days, last_30_days, this_month, etc.)
- `describe_metric(name)` — get metric details
- `describe_model(name)` — get full description of a semantic model
- `describe_dimension(name)` — get full description of a dimension
- `lookup_values(dimension, search)` — find actual values in a dimension (fuzzy)
- `query_metric(metrics, group_by, time_grain, filters, order, limit, compare_period, include_share)` — query one or more metrics. Use compare_period='month' for period comparison, include_share=True for % breakdown. Pass multiple metrics in one call when user asks for them together (e.g. ``metrics=["revenue", "clicks"]``)
- `export(format)` — export last result (format: csv | excel | sheets)
- `generate_chart()` — generate a chart from the last query result
- `disambiguate(entity_type, concept)` — find metrics or dimensions matching a concept (name, synonym, or description). If it returns exactly one match, use that metric/dimension directly. Only ask for clarification when it returns multiple matches.
  - BSL auto-detects chart type from the data (line for time series, pie for few categories, bar otherwise)
  - In Slack the chart is uploaded; in web UI the tool returns the file path
  - Requires a previous query_metric call with group_by dimensions

## How to Query Data

1. Pick the metric(s) (use `list_catalog` if unsure). You can query multiple metrics in one call; all must be from the same semantic model.
   - **IMPORTANT:** When the user asks for multiple metrics in the same query (e.g. "revenue and clicks", "show orders, revenue, units"), combine them in one call: `metrics=["revenue", "clicks", "units"]`. Do NOT make separate calls for each metric.
   - When the user mentions a metric-like term (e.g. "income", "sales", "transactions"), use the Vocabulary above or call `disambiguate(entity_type="metric", concept="...")` to resolve it. If it maps to exactly one metric, use it — do not ask for clarification.
2. If user mentions a specific entity, use `lookup_values` to find exact value
3. For date ranges, use `suggest_date_range(period)` for common periods (last_7_days, last_30_days, this_month, etc.), or compute manually. Always send **two** filters: one with `op` ">=" and `value` as start date (YYYY-MM-DD), one with `op` "<=" and `value` as end date. Example: `filters=[{{"field": "date", "op": ">=", "value": "2024-02-01"}}, {{"field": "date", "op": "<=", "value": "2025-02-11"}}]`
4. Call `query_metric` with the right parameters
5. Once you have data from `query_metric`, answer the user using that data. Do not call `list_catalog` or `query_metric` again unless the user explicitly asks for something different.
   - When the user confirms or refines a previous request (e.g. "break it down by region for last 7 days"), use the context you already have. Do not call list_catalog again unless the metric or dimensions are unclear.

{examples}

## Disambiguation

When a user mentions a metric or dimension concept, call `disambiguate(entity_type, concept)` to find matches:
- **If exactly one match**: Use it. Do not ask for clarification.
- **If multiple matches**: Ask one focused clarification question, offering only the options returned by `disambiguate`. Example: "Which did you mean: (a) Revenue, (b) Average Order Value?"
- **Never suggest metrics or dimensions that are not in the catalog.** Only offer options from `disambiguate` or `list_catalog`. Do not invent options like "Net Income" or "Gross Income" unless they appear in the tool results.

Some concepts map to multiple dimensions:
- Use `describe_dimension` to check meanings
- Ask the user to clarify

{dimension_glossary}

{vocabulary}

{rules_content}

## Response Formatting

Use clear formatting in responses (optimized for Slack):
- Lead with one short takeaway sentence
- Use `**bold**` for key terms and important numbers
- Use `*italic*` only for subtle emphasis (sparingly)
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
- Keep bullets short and scannable; avoid long paragraphs
- Emoji policy: use at most 1-2 emojis per response, and only when they improve scanability (for example status, warning, or trend). Do not add emojis to every bullet.

## First Message

If the user says hello or asks a vague question, welcome them:
{welcome_examples}

{extra_rules}
{custom_sections}\
{gotchas}

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
    *,
    metadata: Any = None,
    agent_config: Any = None,
    project_root: Path | None = None,
) -> str:
    """Assemble the full system prompt from template + BSL model metadata.

    Args:
        bsl_models: BSL SemanticModel objects keyed by model name.
        metadata: ``SemanticMetadata`` from ``DataAgent`` (descriptions, synonyms, etc.).
        agent_config: AgentConfig from falk_project.yaml (optional).
        project_root: Project root for loading RULES.md (optional).
    """
    today = date.today()
    config = _agent_config_to_dict(agent_config)

    # Extract metadata fields (or empty defaults)
    model_descriptions = getattr(metadata, "model_descriptions", {}) or {}
    dimension_descriptions = getattr(metadata, "dimension_descriptions", {}) or {}
    dimension_display_names = getattr(metadata, "dimension_display_names", {}) or {}
    metric_synonyms = getattr(metadata, "metric_synonyms", None)
    dimension_synonyms = getattr(metadata, "dimension_synonyms", None)
    metric_gotchas = getattr(metadata, "metric_gotchas", None)
    dimension_gotchas = getattr(metadata, "dimension_gotchas", None)

    return SYSTEM_PROMPT_TEMPLATE.format(
        current_date=today.isoformat(),
        day_of_week=today.strftime("%A"),
        database_info=_build_database_info(bsl_models),
        company_context=_build_company_context(config),
        business_context=_build_business_context(
            bsl_models, model_descriptions, dimension_descriptions,
        ),
        knowledge_business=_load_knowledge_business(config, project_root),
        knowledge_gotchas=_load_knowledge_gotchas(config, project_root),
        examples=_build_examples(bsl_models, config),
        dimension_glossary=_build_dimension_glossary(
            bsl_models, dimension_descriptions, dimension_display_names,
        ),
        vocabulary=_build_vocabulary(metric_synonyms, dimension_synonyms)
        if config.get("include_semantic_metadata_in_prompt", True)
        else "",
        rules_content=_load_rules_content(project_root),
        gotchas=_build_gotchas(
            metric_gotchas, dimension_gotchas, config.get("gotchas"),
        )
        if config.get("include_semantic_metadata_in_prompt", True)
        else "",
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

    # Backward compatibility for callers that still pass a raw dict.
    if isinstance(agent_config, dict):
        context = str(
            agent_config.get("context")
            or (agent_config.get("business") or {}).get("description")
            or agent_config.get("description")
            or ""
        ).strip()
        return {
            "context": context,
            "examples": list(agent_config.get("examples") or []),
            "welcome": agent_config.get("welcome") or "",
            "rules": list(agent_config.get("rules") or []),
            "gotchas": list(agent_config.get("gotchas") or []),
            "custom_sections": list(agent_config.get("custom_sections") or []),
            "knowledge_enabled": bool((agent_config.get("knowledge") or {}).get("enabled", True)),
            "knowledge_business_path": str((agent_config.get("knowledge") or {}).get("business_path") or "knowledge/business.md"),
            "knowledge_gotchas_path": str((agent_config.get("knowledge") or {}).get("gotchas_path") or "knowledge/gotchas.md"),
            "knowledge_load_mode": str((agent_config.get("knowledge") or {}).get("load_mode") or "startup").lower(),
            "include_semantic_metadata_in_prompt": bool(agent_config.get("include_semantic_metadata_in_prompt", True)),
        }

    return {
        "context": str(getattr(agent_config, "context", "") or "").strip(),
        "examples": list(getattr(agent_config, "examples", []) or []),
        "welcome": getattr(agent_config, "welcome", "") or "",
        "rules": list(getattr(agent_config, "rules", []) or []),
        "gotchas": list(getattr(agent_config, "gotchas", []) or []),
        "custom_sections": list(getattr(agent_config, "custom_sections", []) or []),
        "knowledge_enabled": bool(getattr(agent_config, "knowledge_enabled", True)),
        "knowledge_business_path": str(getattr(agent_config, "knowledge_business_path", "knowledge/business.md") or "knowledge/business.md"),
        "knowledge_gotchas_path": str(getattr(agent_config, "knowledge_gotchas_path", "knowledge/gotchas.md") or "knowledge/gotchas.md"),
        "knowledge_load_mode": str(getattr(agent_config, "knowledge_load_mode", "startup") or "startup").lower(),
        "include_semantic_metadata_in_prompt": bool(getattr(agent_config, "include_semantic_metadata_in_prompt", True)),
    }


# ---------------------------------------------------------------------------
# Company context
# ---------------------------------------------------------------------------

def _build_company_context(config: dict[str, Any]) -> str:
    desc = str(config.get("context") or "").strip()
    # Backward-compatible fallback for legacy dict format.
    if not desc and isinstance(config.get("business"), dict):
        desc = str((config.get("business") or {}).get("description") or "").strip()
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
    sample_model_measures: list[str] = []
    for _model_name, model in bsl_models.items():
        if not sample_metric:
            measures = list(model.measures) if hasattr(model, "measures") else list(model.get("measures", {}).keys())
            if measures:
                sample_metric = measures[0]
                sample_model_measures = measures
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
        f'- "total {m}" -> query_metric(metrics=["{m}"])',
        f'- "{m} by {d}" -> query_metric(metrics=["{m}"], group_by=["{d}"])',
        f'- "top 10 {d}s by {m}" -> query_metric(metrics=["{m}"], '
        f'group_by=["{d}"], order="desc", limit=10)',
        f'- "{m} for <entity>" -> lookup_values("{d}", "<entity>") -> get exact name -> '
        f'query_metric(metrics=["{m}"], group_by=["{d}"], '
        f'filters=[{{"dimension": "{d}", "op": "=", "value": "<exact>"}}])',
        f'- "{m} by month" -> query_metric(metrics=["{m}"], time_grain="month")',
        f'- "last 12 months of {m}" -> query_metric(metrics=["{m}"], filters=[{{"field": "date", "op": ">=", "value": "<start_YYYY-MM-DD>"}}, {{"field": "date", "op": "<=", "value": "<end_YYYY-MM-DD>"}}]) (compute start/end from today)',
        f'- "compare {m} this month vs last" -> query_metric(metrics=["{m}"], compare_period="month")',
        f'- "what % does each {d} have?" -> query_metric(metrics=["{m}"], group_by=["{d}"], include_share=True)',
        '- "show me a chart" -> generate_chart() (run query_metric first with group_by)',
        '- "daily breakdown for top 2" -> TWO STEPS REQUIRED:',
        f'  1) query_metric(metrics=["{m}"], group_by=["{d}"], order="desc", limit=2)',
        f'  2) query_metric(metrics=["{m}"], group_by=["{d}", "date"], '
        f'filters=[{{"dimension": "{d}", "op": "IN", "value": ["<top1>", "<top2>"]}}])',
        "  CRITICAL: For 'top N with breakdown', always do step 1 first, "
        "then filter by results in step 2.",
        '- "show me a time breakdown as a chart" -> FIRST run query_metric with '
        "time_grain or group_by=[\"date\"] to get time series data, THEN generate_chart(). "
        "BSL auto-detects line chart for time series.",
    ]
    # If we have multiple metrics from the same model, show multi-metric example
    if len(sample_model_measures) >= 2:
        m1, m2 = sample_model_measures[0], sample_model_measures[1]
        lines.append(f'- "{m1} and {m2}" -> query_metric(metrics=["{m1}", "{m2}"])')

    # Append domain hints from agent.yaml (natural language, no tool names needed)
    custom = config.get("examples") or []
    if custom:
        lines.append("")
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
        if isinstance(custom, str):
            return custom.strip()
        if isinstance(custom, list):
            return "\n".join(f"- {ex}" for ex in custom if str(ex).strip())

    # Auto-generate from BSL models
    sample_metric = None
    sample_dimension = None
    for _model_name, model in bsl_models.items():
        if not sample_metric:
            measures = list(model.measures) if hasattr(model, "measures") else list(model.get("measures", {}).keys())
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
# Knowledge files (business.md / gotchas.md)
# ---------------------------------------------------------------------------

def _load_knowledge_file(project_root: Path | None, rel_path: str) -> str:
    if not project_root:
        return ""
    candidate = Path(rel_path)
    full_path = candidate if candidate.is_absolute() else (project_root / candidate)
    if not full_path.exists():
        logger.warning("Knowledge file not found: %s", full_path)
        return ""
    try:
        return full_path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _load_knowledge_business(config: dict[str, Any], project_root: Path | None) -> str:
    if not config.get("knowledge_enabled", True):
        return ""
    # Phase 1 supports startup loading only.
    if str(config.get("knowledge_load_mode") or "startup").lower() != "startup":
        return ""
    content = _load_knowledge_file(project_root, str(config.get("knowledge_business_path") or "knowledge/business.md"))
    if not content:
        return ""
    return f"\n## Knowledge: Business\n{content}\n"


def _load_knowledge_gotchas(config: dict[str, Any], project_root: Path | None) -> str:
    if not config.get("knowledge_enabled", True):
        return ""
    if str(config.get("knowledge_load_mode") or "startup").lower() != "startup":
        return ""
    content = _load_knowledge_file(project_root, str(config.get("knowledge_gotchas_path") or "knowledge/gotchas.md"))
    if not content:
        return ""
    return f"\n## Knowledge: Data Gotchas\n{content}\n"


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
    dimension_display_names: dict[tuple[str, str], str] | None = None,
) -> str:
    """Auto-generate disambiguation hints for ambiguous dimension groups."""
    dimension_descriptions = dimension_descriptions or {}
    dimension_display_names = dimension_display_names or {}
    seen: set[str] = set()
    all_dims: list[tuple[str, str]] = []  # (display_name, desc_short)

    for model_name, model in bsl_models.items():
        for dim_name, dim in model.get_dimensions().items():
            if dim_name in seen:
                continue
            seen.add(dim_name)
            
            # Use display_name if available, otherwise fall back to technical name
            display_name = dimension_display_names.get((model_name, dim_name), "") or dim_name
            
            desc = dimension_descriptions.get((model_name, dim_name)) or ""
            desc = desc.replace("\r\n", " ").replace("\n", " ").strip()
            dot = desc.find(".")
            if dot > 0:
                desc = desc[:dot + 1]
            all_dims.append((display_name, desc))

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

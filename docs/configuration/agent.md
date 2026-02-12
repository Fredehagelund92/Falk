# Project Configuration

`falk_project.yaml` is the technical configuration for your falk project (in project root). It controls agent behavior, extensions, and access control.

> **Note:** Business context and rules live in `RULES.md` and `knowledge/` files. See [Context Engineering](../concepts/context-engineering.md).

## Sections

### `agent` — LLM settings and behavior

```yaml
agent:
  provider: anthropic        # anthropic, openai, gemini
  model: claude-sonnet-4     # Model to use
  
  # Business context (brief summary)
  context: |
    We're a SaaS company selling analytics software.
    The funnel is: trials -> signups -> paid customers -> revenue.
  
  # Example questions (shown to users)
  examples:
    - "What's our revenue by region this month?"
    - "Show me top 5 customers by trials"
  
  # Rules the agent should follow
  rules:
    - "Revenue data has a 24-hour processing delay"
    - "Always mention the date range when showing results"
  
  # Welcome message for new conversations
  welcome: |
    👋 Hi! I can help you explore your data.
    Try asking: "What's our revenue by region?"
```

### `extensions` — Integrations

```yaml
extensions:
  langfuse:
    enabled: true
    trace_all: true
    collect_feedback: true
  
  slack:
    enabled: true
    feedback_reactions: true
    channels: []  # Empty = all channels
  
  charts:
    enabled: true
    default_type: auto  # auto, bar, line, pie
    formats: [png, html]
  
  exports:
    enabled: true
    formats: [csv, excel, google_sheets]
    max_rows: 100000
```

### `access` — Data governance

```yaml
access:
  # access_policy: access_policy.yaml  # If set and file exists, row-level filtering enabled
```

### `skills` — Bring your own skills

```yaml
skills:
  enabled: false
  directories: ["./skills"]
```

See [Agent Skills](./skills.md) for details.

### `connection` — Database (inline)

```yaml
connection:
  type: duckdb
  database: data/warehouse.duckdb
```

BigQuery: `type: bigquery`, `project_id`, `dataset_id`. Snowflake: `type: snowflake`, `user`, `password`, `account`, `database`, `schema`.

### `paths` — File locations

```yaml
paths:
  semantic_models: semantic_models.yaml
```

### `advanced` — Technical settings

```yaml
advanced:
  auto_run: false
  max_tokens: 4096
  temperature: 0.1
  max_rows_per_query: 10000
  query_timeout_seconds: 30
  max_retries: 3
  log_level: INFO
```

## Full Example

```yaml
version: 1

connection:
  type: duckdb
  database: data/warehouse.duckdb

agent:
  provider: anthropic
  model: claude-sonnet-4
  context: |
    We're a SaaS analytics company.
  rules:
    - "Revenue data has a 48-hour delay"
  examples:
    - "What's our revenue by region?"

extensions:
  langfuse:
    enabled: true
  charts:
    enabled: true
  exports:
    enabled: true

access:
  # access_policy: access_policy.yaml  # optional

paths:
  semantic_models: semantic_models.yaml

advanced:
  auto_run: false
  max_tokens: 4096
  temperature: 0.1
  max_rows_per_query: 10000
  query_timeout_seconds: 30
```

## Relationship to Other Config Files

| File | Purpose |
|------|---------|
| `falk_project.yaml` | Technical config (LLM, extensions, access) |
| `semantic_models.yaml` | Data layer (metrics, dimensions, synonyms) |
| `RULES.md` | Agent behavior rules (included in every conversation) |
| `knowledge/` | Business terms, data quality gotchas (loaded as needed) |
| `.env` | API keys and secrets |

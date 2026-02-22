# Project Configuration

`falk_project.yaml` is the canonical runtime configuration for falk.
It controls model behavior, prompt extensions, session storage, observability,
and runtime limits.

## Canonical Config Surface

```yaml
version: 1

connection:
  type: duckdb
  database: data/warehouse.duckdb

agent:
  provider: openai
  model: gpt-5-mini
  context: |
    We are a B2B SaaS company selling analytics software.

  examples:
    - "What is revenue by region this month?"
    - "Top 5 customers by revenue"

  rules:
    - "Always mention the date range used."
    - "Revenue has a 24-hour delay."

  gotchas:
    - "Data from today may be incomplete before daily refresh."

  welcome: |
    Hi! I can help you explore your data.

  custom_sections:
    - title: Reporting Conventions
      content: |
        - Use USD unless requested otherwise.
        - Round percentages to one decimal place.

  knowledge:
    enabled: true
    business_path: knowledge/business.md
    gotchas_path: knowledge/gotchas.md
    load_mode: startup   # startup (phase 1), on_demand reserved

  # Custom Python tool extensions (see concepts/tools.md)
  extensions:
    tools:
      - module: project_tools.customer_health
      - module: project_tools.forecasting
      - module: project_tools.alerts
        enabled: false

# Observability: set LOGFIRE_TOKEN in .env for Logfire Cloud tracing (optional)

session:
  store: memory         # memory (default) or postgres (production)
  postgres_url: ${POSTGRES_URL}
  schema: falk_session
  ttl: 3600
  maxsize: 500

slack:
  exports_dm_only: true
  export_channel_allowlist: []   # optional channel IDs allowed for exports
  export_block_message: "Export files are restricted to DMs. Ask me in DM if you need the file."

paths:
  semantic_models: semantic_models.yaml

advanced:
  auto_run: false                 # reserved for future use
  max_tokens: 4096
  temperature: 0.1
  max_rows_per_query: 10000
  query_timeout_seconds: 30       # warehouse/tool execution
  model_timeout_seconds: 60       # LLM request (single turn)
  max_retries: 3
  retry_delay_seconds: 1
  log_level: INFO
```

## What Is Applied at Runtime

### `agent`
- `context`, `examples`, `rules`, `gotchas`, `welcome`, and `custom_sections` are injected into prompt construction.
- `knowledge.*` controls startup loading of `knowledge/business.md` and `knowledge/gotchas.md`.
- `extensions.tools` registers custom Python tool modules. Each module must export a `FunctionToolset` (as `toolset`, `data_tools`, or `tools`). Tools are loaded at startup and exposed in both the agent (chat, web, Slack) and MCP server. See [Custom Tool Extensions](../concepts/tools.md#custom-tool-extensions).

### `advanced`
- `max_tokens`, `temperature`, `model_timeout_seconds`, and `max_retries` are applied to model execution (LLM request timeout).
- `query_timeout_seconds` is the timeout for tool execution (e.g. warehouse queries); tune it separately from `model_timeout_seconds` if you see "query took too long" from slow DB vs slow model.
- `slack_run_timeout_seconds` is the timeout for a whole Slack run (model + tools), used by the Slack bot's outer `future.result(timeout=...)`.
- `tool_calls_limit` is the maximum number of tool calls allowed per run; lower values stop tool loops sooner.
- `request_limit` is the maximum number of LLM turns per run.
- `max_rows_per_query` and retry settings are enforced in warehouse query execution.
- `log_level` and timeout settings are applied in Slack runtime behavior.
- `auto_run` is reserved for future use.

### `session`
- `memory` (default) — works out of the box for local development.
- `postgres` for production — requires `POSTGRES_URL` in `.env`. Falk creates schema and tables automatically. Server fails at startup if postgres is configured but URL is invalid.
- Session config precedence is: environment variables > `falk_project.yaml` > defaults.
  - `SESSION_STORE`, `POSTGRES_URL`, `SESSION_SCHEMA`, `SESSION_TTL`, `SESSION_MAXSIZE`
- Persisted session state is JSON-only (`last_query_data`, `last_query_metric`, `pending_files`).
- Chart aggregate objects are process-local and ephemeral; if unavailable (restart/worker switch), rerun `query_metric` before `generate_chart`.

### `slack`
- `exports_dm_only: true` blocks export/chart file uploads in non-DM channels.
- `export_channel_allowlist` can allow specific channel IDs when you decide to widen policy.
- `export_block_message` controls the user-visible notice shown when export delivery is blocked in-channel.

### Observability
- Set `LOGFIRE_TOKEN` in `.env` to enable Logfire Cloud tracing and feedback (optional).

### `paths`
- `paths.semantic_models` controls semantic model file resolution.

### `connection`
- Inline database connection profile consumed by BSL.

## Related Files

| File | Purpose | Loaded |
|---|---|---|
| `falk_project.yaml` | Canonical config and short inline context | Startup |
| `semantic_models.yaml` | Metrics, dimensions, synonyms, model metadata | Startup |
| `RULES.md` | Organization-wide response/process policy | Startup (included in prompt) |
| `knowledge/business.md` | Domain/company context | Startup when `agent.knowledge.enabled: true` |
| `knowledge/gotchas.md` | Data caveats and known issues | Startup when `agent.knowledge.enabled: true` |
| `.env` | Secrets | Startup |

## Phase 2 Note

Access policy / row-level governance is intentionally deferred to phase 2.

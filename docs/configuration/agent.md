# Project Configuration

`falk_project.yaml` is the canonical runtime configuration. It controls model behavior, prompt extensions, session storage, observability, and runtime limits.

## Config overview

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
    load_mode: startup

  extensions:
    tools:
      - module: project_tools.customer_health
      - module: project_tools.forecasting
      - module: project_tools.alerts
        enabled: false

session:
  store: memory         # memory (default) or postgres (production)
  postgres_url: ${POSTGRES_URL}
  schema: falk_session
  ttl: 3600
  maxsize: 500

slack:
  exports_dm_only: true
  export_channel_allowlist: []
  export_block_message: "Export files are restricted to DMs. Ask me in DM if you need the file."

paths:
  semantic_models: semantic_models.yaml

advanced:
  auto_run: false
  max_tokens: 4096
  temperature: 0.1
  max_rows_per_query: 10000
  query_timeout_seconds: 30
  model_timeout_seconds: 60
  max_retries: 3
  retry_delay_seconds: 1
  log_level: INFO
```

## What is applied at runtime

### `agent`

- `context`, `examples`, `rules`, `gotchas`, `welcome`, and `custom_sections` are injected into prompt construction.
- `knowledge.*` controls startup loading of `knowledge/business.md` and `knowledge/gotchas.md`.
- `extensions.tools` registers custom Python tool modules. See [Custom Tool Extensions](/concepts/tools#custom-tool-extensions).

### `advanced`

- `max_tokens`, `temperature`, `model_timeout_seconds`, and `max_retries` apply to model execution.
- `query_timeout_seconds` is the timeout for tool execution (warehouse queries).
- `max_rows_per_query` and retry settings are enforced in warehouse query execution.

### `session`

- `memory` (default) — works out of the box for local development.
- `postgres` for production — requires `POSTGRES_URL` in `.env`. falk creates schema and tables automatically.
- Session config precedence: environment variables > `falk_project.yaml` > defaults.

See [Memory](/concepts/memory) for the persistence model and when to use each store.

### `slack`

- `exports_dm_only: true` blocks export/chart file uploads in non-DM channels.
- `export_channel_allowlist` can allow specific channel IDs.
- `export_block_message` controls the user-visible notice when export is blocked.

### Observability

Set `LOGFIRE_TOKEN` in `.env` to enable Logfire Cloud tracing (optional).

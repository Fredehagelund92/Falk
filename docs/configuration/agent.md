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

observability:
  langfuse_sync: true

session:
  store: memory          # memory or redis
  url: redis://localhost:6379
  ttl: 3600
  maxsize: 500

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

### `advanced`
- `max_tokens`, `temperature`, `model_timeout_seconds`, and `max_retries` are applied to model execution (LLM request timeout).
- `query_timeout_seconds` is the timeout for tool execution (e.g. warehouse queries); tune it separately from `model_timeout_seconds` if you see "query took too long" from slow DB vs slow model.
- `max_rows_per_query` and retry settings are enforced in warehouse query execution.
- `log_level` and both timeout settings are applied in Slack runtime behavior.
- `auto_run` is reserved for future use.

### `session`
- `memory` for single-process deployments.
- `redis` for multi-worker deployments.

### `observability`
- `langfuse_sync` controls Langfuse flush behavior.
- Langfuse is active when the required env vars are set.

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

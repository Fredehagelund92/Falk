---
sidebar_position: 2
---

# State

falk manages two kinds of runtime state: per-request (ephemeral) and per-session (persisted).

## Request state

Exists only for a single turn or tool run. Not stored anywhere.

- Tool inputs and outputs during one agent response
- LLM reasoning and tool-call decisions
- Temporary execution context

When the response completes, request state is discarded.

## Session state

Persists across turns in a conversation. Stored in the [session store](/concepts/memory#session-memory).

| Field | Purpose |
|-------|---------|
| `last_query_data` | Last query result (for export, chart) |
| `last_query_params` | Metrics, filters, group_by (for chart re-run) |
| `pending_files` | Files queued for upload (e.g. Slack) |

**Session ID** is derived from context:

- Slack: `thread_ts` (one session per thread)
- Web/CLI: `user_id` or `channel:user_id`
- MCP: `default` if no metadata

Follow-up questions in the same thread reuse the same session, so "export that to CSV" or "show me a chart" work without re-running the query.

## Restart and reset

| Store | Survives restart? |
|-------|-------------------|
| `memory` | No — in-process only |
| `postgres` | Yes — persisted to database |

Chart generation uses session state. If the process restarts with `memory` store, chart context is lost — rerun the query to regenerate.

See [Memory](/concepts/memory) for persistence options and configuration.

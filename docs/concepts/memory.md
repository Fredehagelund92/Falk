---
sidebar_position: 3
---

# Memory

What the agent "remembers" falls into four categories. Only session memory is configurable; the rest are fixed by design.

## What persists

| Scope | Storage | Survives restart? | Edited by |
|-------|---------|------------------|-----------|
| Request | None (ephemeral) | No | — |
| Session | `memory` or `postgres` | `memory`: no, `postgres`: yes | Agent (during conversation) |
| Knowledge | Files (`semantic_models.yaml`, `RULES.md`, `knowledge/*.md`) | Yes | Humans (version-controlled) |
| Feedback | Logfire (optional) | Yes | Agent (traces) + humans (scores) |

## Session memory

Conversation history and runtime state (last query, pending files) live in the session store.

| Option | Use case |
|--------|----------|
| `memory` (default) | Local dev, single process. Works out of the box. |
| `postgres` | Production, multi-worker. Requires `POSTGRES_URL` in `.env`. |

Configure in `falk_project.yaml`:

```yaml
session:
  store: memory         # or postgres
  postgres_url: ${POSTGRES_URL}
  schema: falk_session
  ttl: 3600             # seconds before session expires
  maxsize: 500           # max sessions (memory store only)
```

See [Project Config](/configuration/agent#session) for full options.

## Knowledge memory (static)

Loaded at startup from version-controlled files. The agent does not learn from conversations; it reads from:

- `semantic_models.yaml` — metrics, dimensions, synonyms, gotchas
- `RULES.md` — behavior, tone, formatting
- `knowledge/business.md`, `knowledge/gotchas.md` — when `agent.knowledge.enabled: true`

See [Context](/concepts/context) for what goes where.

## Feedback traces

👍/👎 reactions and traces go to Logfire (if configured). Used for offline improvement — data stewards review low scores and update config files. The agent does not auto-update from feedback.

See [Learning & Feedback](/concepts/learning) for the improvement cycle.

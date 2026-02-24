# Logfire Observability

Logfire provides tracing, cost tracking, and feedback for your data agent.

## What Logfire adds

| Feature | Without Logfire | With Logfire |
|---------|-----------------|--------------|
| **Feedback** | Logged (not persisted) | Structured feedback with scores |
| **Observability** | None | Full traces (LLM calls, tools) |
| **Cost tracking** | None | Token usage and API costs per query |

## Setup

### Development

No environment variable needed. Credentials are stored locally in `.logfire/`.

1. Authenticate:

```bash
uv run logfire auth
```

2. Create a project in the Logfire UI (or use an existing one).

3. Set the Logfire project:

```bash
uv run logfire projects use <project-name>
```

Run from the directory where you start `falk chat`, `falk mcp`, or `falk slack`.

### Production

1. Create a write token in the Logfire UI (Project Settings → Write Tokens).
2. Add to `.env`:

```bash
LOGFIRE_TOKEN=...
```

The agent will automatically trace runs when Logfire is configured.

## What gets traced

Every agent interaction creates a **trace** with:

- User query
- Agent response
- Tool calls (query_metric, export, etc.)
- Model info (LLM used, token usage, cost)
- Metadata (user ID, channel, thread for Slack)

## Feedback collection

When users react with thumbs up/down in Slack:

- **👍** — Score of `1.0` recorded in Logfire
- **👎** — Score of `0.0` recorded in Logfire

Feedback is linked to the trace via `trace_id`.

## Fallback behavior

If Logfire is **not configured**:

- Agent works normally
- Feedback is logged to console but not persisted
- No traces or cost tracking

## Troubleshooting

**"Logfire env vars set but package not installed"** — Run `uv sync`.

**No traces appearing** — Run `uv run logfire auth` then `uv run logfire projects use <project-name>` from your project root. For production, verify `LOGFIRE_TOKEN` is in `.env`.

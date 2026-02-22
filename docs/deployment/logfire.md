# Logfire Observability

Logfire provides tracing, cost tracking, and feedback for your data agent.

## What Logfire Adds

| Feature | Without Logfire | With Logfire |
|---|---|---|
| **Feedback** | Logged (not persisted) | Structured feedback with scores |
| **Observability** | None | Full traces (LLM calls, tools) |
| **Cost tracking** | None | Token usage and API costs per query |

## Setup

### Development (recommended for local use)

No environment variable needed. Credentials are stored locally in `.logfire/`.

1. Authenticate:

```bash
uv run logfire auth
```

2. Create a project in the Logfire UI (or use an existing one).

3. From your project root, set the Logfire project:

```bash
uv run logfire projects use <project-name>
```

This creates a `.logfire/` directory and stores your token locally. Run from the directory where you start `falk chat`, `falk mcp`, or `falk slack`.

### Production

For deployed applications, use a write token:

1. Create a write token in the Logfire UI (Project Settings → Write Tokens).
2. Add to your `.env`:

```bash
LOGFIRE_TOKEN=...
```

(Or `LOGTAIL_TOKEN` for legacy compatibility.)

That's it. The agent will automatically trace runs when Logfire is configured.

## What Gets Traced

Every agent interaction creates a **trace** in Logfire with:

- **User query** — The original question
- **Agent response** — The final answer
- **Tool calls** — Each tool invocation (query_metric, export, etc.)
- **Model info** — Which LLM was used, token usage, cost
- **Metadata** — User ID, channel, thread (for Slack)

## Feedback Collection

When users react with thumbs up/down in Slack:

- **Positive (👍)** — Score of `1.0` recorded in Logfire
- **Negative (👎)** — Score of `0.0` recorded in Logfire

Feedback is linked to the trace via `trace_id`.

## Fallback Behavior

If Logfire is **not configured** (no `LOGFIRE_TOKEN`, no `.logfire/` from `logfire projects use`):

- Agent works normally
- Feedback is logged to console but not persisted
- No traces or cost tracking

## Troubleshooting

### "Logfire env vars set but package not installed"

```bash
uv sync
```

### No traces appearing

- **Development:** Run `uv run logfire auth` then `uv run logfire projects use <project-name>` from your project root.
- **Production:** Verify `LOGFIRE_TOKEN` is in `.env`.
- Check agent logs for Logfire warnings.

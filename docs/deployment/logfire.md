# Logfire Observability

Logfire provides tracing, cost tracking, and feedback for your data agent.

## What Logfire Adds

| Feature | Without Logfire | With Logfire |
|---|---|---|
| **Feedback** | Logged (not persisted) | Structured feedback with scores |
| **Observability** | None | Full traces (LLM calls, tools) |
| **Cost tracking** | None | Token usage and API costs per query |

## Setup

### 1. Authenticate

```bash
logfire auth
```

### 2. Create a project

```bash
logfire projects new
```

### 3. Configure environment

Add to your `.env` file:

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

If Logfire is **not configured** (LOGFIRE_TOKEN not set):

- Agent works normally
- Feedback is logged to console but not persisted
- No traces or cost tracking

## Troubleshooting

### "Logfire env vars set but package not installed"

```bash
uv sync
```

### No traces appearing

- Run `logfire auth` and `logfire projects new`
- Verify LOGFIRE_TOKEN is in `.env`
- Check agent logs for Logfire warnings

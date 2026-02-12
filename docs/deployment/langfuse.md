# LangFuse Observability

LangFuse provides full observability, cost tracking, and evaluation for your data agent.

## What LangFuse Adds

| Feature | Without LangFuse | With LangFuse |
|---|---|---|
| **Feedback** | Logged (not persisted) | Structured feedback with scores |
| **Observability** | None | Full traces (LLM calls, tools, chain-of-thought) |
| **Cost tracking** | None | Token usage and API costs per query |
| **Evaluation** | None | A/B testing, custom evaluations |
| **Prompt versioning** | None | Track prompt changes over time |

## Setup

### 1. Get LangFuse Keys

**Option A: Cloud (recommended for most users)**
- Sign up at https://cloud.langfuse.com
- Free tier available
- Get your `LANGFUSE_SECRET_KEY` and `LANGFUSE_PUBLIC_KEY`

**Option B: Self-hosted**
- Deploy LangFuse on your infrastructure
- Set `LANGFUSE_HOST` to your instance URL

### 2. Configure Environment

Add to your `.env` file:

```bash
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com  # Optional, defaults to cloud
```

### 3. Install Dependencies

```bash
   uv sync
```

That's it! The agent will automatically start tracing if LangFuse is configured.

## What Gets Traced

Every agent interaction creates a **trace** in LangFuse with:

- **User query** — The original question
- **Agent response** — The final answer
- **Tool calls** — Each tool invocation (query_metric, export_to_csv, etc.)
- **Model info** — Which LLM was used, token usage, cost
- **Metadata** — User ID, channel, thread (for Slack)

## Feedback Collection

When users react with 👍 or 👎 in Slack:

- **Positive (👍)** → Score of `1.0` recorded in LangFuse
- **Negative (👎)** → Score of `0.0` recorded in LangFuse

The feedback is automatically linked to the trace, so you can see:
- Which queries users liked/disliked
- What tools were used for successful queries
- Patterns in negative feedback (for improvement)

## Using LangFuse Dashboard

### View Traces

1. Go to your LangFuse dashboard
2. Navigate to **Traces**
3. See all agent interactions with:
   - Query text
   - Response
   - Tool calls
   - Token usage
   - Cost
   - User feedback scores

### Analyze Costs

1. Go to **Analytics** → **Costs**
2. See:
   - Total spend over time
   - Cost per query
   - Cost per user
   - Model breakdown

### Evaluate Prompts

1. Create an **Evaluation** in LangFuse
2. A/B test different prompt versions
3. Measure quality improvements
4. Track metrics over time

## Fallback Behavior

If LangFuse is **not configured** (env vars not set):

- ✅ Agent works normally
- ⚠️ Feedback is logged to console but not persisted (configure LangFuse for full tracking)
- ❌ No traces, cost tracking, or evaluation

This makes LangFuse **opt-in** — you can use the agent without it, and add it later when needed.

## Troubleshooting

### "LangFuse env vars set but package not installed"

```bash
   uv sync
```

### "Failed to initialize LangFuse"

- Check your `LANGFUSE_SECRET_KEY` and `LANGFUSE_PUBLIC_KEY`
- Verify `LANGFUSE_HOST` is correct (if self-hosting)
- Check network connectivity to LangFuse

### No traces appearing

- Verify env vars are loaded (check `.env` file)
- Check LangFuse dashboard for errors
- Look for warnings in agent logs

## Advanced: Custom Evaluations

You can create custom evaluation functions in LangFuse to:

- Measure response quality
- Check for specific patterns
- Compare different prompt versions
- Track improvements over time

See [LangFuse documentation](https://langfuse.com/docs) for details.


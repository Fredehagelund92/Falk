# How It Works

## Architecture

```
User (Slack / Web UI / CLI)
     │
     ▼
Pydantic AI Agent
     │
     ├── System Prompt (auto-generated from RULES.md + semantic models)
     ├── Tools (query, export, chart, metadata)
     │     │
     │     ▼
     │   BSL Semantic Layer → Database
     │
     └── Feedback → LangFuse (optional)
```

## Flow

1. **User asks a question** — "top 10 regions by sales last month"
2. **Agent reads system prompt** — includes RULES.md, business context, synonyms, gotchas
3. **Agent resolves vocabulary** — "sales" → `revenue` (from synonyms)
4. **Agent calls tools** — `query_metric(metric="revenue", group_by=["region"], order="desc", limit=10)`
5. **BSL generates the query** — from semantic model definitions
6. **Database executes** — returns data
7. **Agent checks gotchas** — e.g., "Revenue has a 48-hour delay"
8. **Agent formats response** — Slack-optimised (bullets, bold, no tables)
9. **User reacts** — feedback sent to LangFuse

## The knowledge layer

The system prompt is assembled **automatically** from three sources:

| Source | What it contributes |
|--------|---------------------|
| `semantic_models.yaml` | Metrics, dimensions, synonyms, gotchas |
| `RULES.md` | Agent behavior, tone, orchestration rules |
| `knowledge/` | Domain knowledge (loaded at startup when enabled) |

You never edit the prompt directly. Update your config files and the prompt updates itself.

### Gotchas

Gotchas are injected into the system prompt so the agent can proactively warn users:

```yaml
measures:
  revenue:
    expr: _.revenue.sum()
    gotchas: "Revenue has a 48-hour reporting delay"
```

When someone asks "what was our revenue yesterday?", the agent mentions the delay.

## Entity resolution

When a user says "sales for Acme Corp", the agent:

1. Calls `lookup_values("customer", "Acme Corp")` — fuzzy search
2. Gets the exact match
3. Uses it as a filter

Works for partial matches too — "acme" finds "Acme Corp".

## Conversational delivery

Large results don't get dumped:

- **≤10 rows** → shown inline
- **>10 rows** → preview + "Want top 10? Export to CSV? Chart?"

The agent asks how you want to consume the data.

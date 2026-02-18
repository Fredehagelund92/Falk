# falk

> **Governed AI access to your data warehouse, powered by semantic layers.**

Define metrics once in YAML. Query them naturally through Slack, CLI, or web.
Same numbers everywhere. No SQL generation. No prompt engineering.

## The idea

Most AI data agents let models write raw SQL over your warehouse. That's powerful for exploration — but dangerous for production, where "revenue" needs to mean the same thing every time.

**falk puts your semantic layer in charge.** The agent reads governed metric definitions instead of guessing from table schemas. Every query goes through the same calculations your BI tools use.

```yaml
# semantic_models.yaml — define once, query everywhere
sales_metrics:
  measures:
    revenue:
      expr: _.amount.sum()
      description: "Total revenue (completed orders only)"
      synonyms: ["sales", "income"]
      related_metrics: [orders, average_order_value]
```

## What you get

- **Governed access** — only approved metrics and dimensions, not raw tables
- **MCP server** — standard protocol for AI tools (Cursor, Claude Desktop, any MCP client)
- **Consistent numbers** — same calculation as your BI layer
- **Business context** — synonyms, gotchas, and rules built into the schema
- **Automatic root cause** — ask "why did revenue increase?" and get a real answer
- **Multi-interface** — MCP server, Slack, web UI — same data everywhere

## Quick start

```bash
git clone https://github.com/Fredehagelund92/Falk.git
cd falk && uv venv && uv sync

falk init my-project
cd my-project

# Add your API key
cp .env.example .env  # edit: OPENAI_API_KEY=sk-...

# Validate configuration
falk test --fast

# Start MCP server (connect from Cursor, Claude Desktop)
falk mcp

# OR start web UI
falk chat   # localhost:8000

# OR start Slack bot
falk slack
```

## Learn more

| Topic | Description |
|---|---|
| [Why falk?](why-falk.md) | The philosophy behind semantic-layer AI |
| [Quick Start](getting-started/quickstart.md) | Full setup walkthrough |
| [Semantic Models](configuration/semantic-models.md) | Define your metrics |
| [CLI Reference](cli-reference.md) | All commands |
---

## Inspiration & Credits

falk was inspired by excellent work in the data agent space:

- **[OpenAI's in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/)** — Grounded metric querying and data agents
- **[nao](https://github.com/getnao/nao)** — Context engineering patterns and agent reliability testing
- **[dash](https://github.com/agno-agi/dash)** — Self-learning from feedback and six layers of context

We're grateful to these projects for showing what's possible with well-designed data agents.

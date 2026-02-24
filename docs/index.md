---
slug: /
sidebar_position: 1
---

# Falk

**Governed AI access to your data warehouse, powered by semantic layers.**

Define metrics once in YAML. Query them naturally through Slack, CLI chat, or MCP. Same numbers everywhere.

## Why Falk

Most AI SQL agents can answer fast but drift on metric definitions. Falk puts the semantic layer in charge, so AI uses approved metrics and dimensions only.

- One metric definition in YAML, reused everywhere
- Governed access instead of free-form warehouse querying
- Consistent numbers across Slack, CLI, web, and MCP

## What you get

- **Governed access** — only approved metrics and dimensions, not raw tables
- **MCP server** — works with Cursor, Claude Desktop, and any MCP client
- **Consistent numbers** — same as your BI layer
- **Business context** — synonyms, gotchas, and rules built into the schema
- **"Why" questions** — ask "why did revenue increase?" and get a real answer
- **Multi-interface** — MCP server, Slack, CLI chat — same data everywhere

## Quick start

Get a working project in under 5 minutes:

```bash
git clone https://github.com/Fredehagelund92/Falk.git
cd Falk && uv venv && uv sync

falk init my-project
cd my-project

cp .env.example .env   # Add your OPENAI_API_KEY
falk validate --fast

# Start querying
falk chat      # Web UI at http://127.0.0.1:8000
# or
falk mcp       # Connect from Cursor or Claude Desktop
# or
falk slack     # Deploy for your team
```

## Learn more

| Topic | Description |
|-------|-------------|
| [Quick Start](getting-started/quickstart) | Full setup walkthrough |
| [State & Memory](concepts/memory) | What persists across requests and sessions |
| [Learning & Feedback](concepts/learning) | How the agent improves over time |
| [Semantic Models](configuration/semantic-models) | Define your metrics |
| [CLI Reference](cli-reference) | All commands |

## Deployment note (0.1.0)

- **Alpha** — not battle-tested for production yet. Use at your own risk.
- Recommended: one company/workspace per deployment (single-tenant).
- In production (`FALK_ENV=production`), configure `access_policies` to avoid open access.
- Session storage defaults to memory. For production, set `session.store: postgres` and `POSTGRES_URL` in `.env`. See [Memory](concepts/memory).
- Chart generation uses session state; rerun the query if a restart drops chart context.
- Slack exports default to DM-only; optionally allow channels via `slack.export_channel_allowlist`.

## Inspiration & Credits

falk was inspired by excellent work in the data agent space:

- **[OpenAI's in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/)** — Grounded metric querying and data agents
- **[nao](https://github.com/getnao/nao)** — Context engineering patterns and agent reliability testing
- **[dash](https://github.com/agno-agi/dash)** — Self-learning from feedback and six layers of context

We're grateful to these projects for showing what's possible with well-designed data agents.

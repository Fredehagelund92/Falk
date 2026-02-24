# Quick Start

Get a working falk project in under 5 minutes.

## 1. Install

```bash
git clone https://github.com/Fredehagelund92/Falk.git
cd Falk
uv venv && uv sync
```

## 2. Create a project

```bash
falk init my-analytics
cd my-analytics
```

This creates a project with:

- `RULES.md` — agent behavior rules
- `knowledge/` — business context and known caveats
- `evals/` — starter eval cases
- `semantic_models.yaml` — metrics and dimensions
- `falk_project.yaml` — agent config
- `data/warehouse.duckdb` — sample data (90 days)
- `.env.example` — environment template

## 3. Add your API key

```bash
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-...
```

## 4. Verify

```bash
falk validate --fast
```

You should see: `Configuration valid!`

## 5. Start querying

```bash
# Option 1: Web UI
falk chat
# Opens at http://localhost:8000

# Option 2: MCP server (connect from Cursor or Claude Desktop)
falk mcp
```

Try asking:

- "What's our total revenue?"
- "Top 5 regions by revenue"
- "Compare revenue this month vs last"

## 6. Make it yours

### Define your metrics

Edit `semantic_models.yaml` to add your tables, dimensions, and measures. See [Semantic Models](/configuration/semantic-models) for the full reference.

### Add business context

Edit `RULES.md` and fill in `knowledge/` files with your domain knowledge. See [Context Engineering](/concepts/context-engineering).

### Deploy to Slack

```bash
# Add Slack tokens to .env
falk slack
```

## Next steps

- [Semantic Models](/configuration/semantic-models) — full configuration reference
- [Context Engineering](/concepts/context-engineering) — teach the agent about your business
- [CLI Reference](/cli-reference) — all commands
- [Slack Bot](/deployment/slack) — deploy for your team

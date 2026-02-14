# Quick Start

Get a working falk project in under 5 minutes.

## 1. Install

```bash
git clone https://github.com/Fredehagelund92/Falk.git
cd falk
uv venv && uv sync
```

## 2. Create a project

```bash
falk init my-analytics
cd my-analytics
```

This creates:

```text
my-analytics/
├── RULES.md                    # Agent behavior rules
├── knowledge/                  # Business knowledge
│   ├── business/
│   │   ├── glossary.md
│   │   └── context.md
│   ├── domains/
│   │   ├── marketing.md
│   │   ├── finance.md
│   │   └── product.md
│   └── data-quality.md
├── semantic_models.yaml       # Metrics & dimensions
├── falk_project.yaml          # Agent config
├── data/
│   └── warehouse.duckdb       # Sample data (90 days)
└── .env.example
```

## 3. Add your API key

```bash
cp .env.example .env
# Edit .env: OPENAI_API_KEY=sk-...
```

## 4. Verify

```bash
falk test --fast
```

```text
✅ Configuration valid!
  ✓ Semantic models: 1 model, 6 metrics, 4 dimensions
```

## 5. Start querying

```bash
# List available metrics
falk metrics list

# Query a metric
falk query revenue --group-by region

# Why did revenue change?
falk decompose revenue --period month

# Web UI
falk chat
# → http://localhost:8000
```

Try asking in the web UI:

- "What's our total revenue?"
- "Top 5 regions by revenue"
- "Why did revenue change this month?"

## 6. Make it yours

### Define your metrics

Edit `semantic_models.yaml`:

```yaml
my_model:
  table: my_table
  database: [my_schema]
  description: "What this model represents"
  dimensions:
    date:
      expr: _.date
      is_time_dimension: true
    region:
      expr: _.region
      description: "Sales region"
      synonyms: ["territory", "area"]
  measures:
    revenue:
      expr: _.revenue.sum()
      description: "Total revenue (completed orders)"
      synonyms: ["sales", "income"]
      related_metrics: [orders, average_order_value]
```

### Add business context

Edit `RULES.md` and fill in `knowledge/` files with your domain knowledge. See [Context Engineering](../concepts/context-engineering.md).

### Deploy to Slack

```bash
# Add Slack tokens to .env
falk slack
```

## Next steps

- [Semantic Models](../configuration/semantic-models.md) — full configuration reference
- [Context Engineering](../concepts/context-engineering.md) — teach the agent about your business
- [CLI Reference](../cli-reference.md) — all commands
- [Slack Bot](../deployment/slack.md) — deploy for your team

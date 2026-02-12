# falk

> **Governed AI access to your data warehouse, powered by semantic layers.**

Define metrics once in YAML. Query them naturally through Slack, CLI, or web.
Same numbers everywhere. No SQL generation. No prompt engineering.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## Why falk?

Most AI data agents let models write raw SQL. That's great for exploration — but when "revenue" needs to mean the same thing everywhere, you need governance.

**falk puts your semantic layer in charge.** Metrics are defined once, and every query goes through the same calculations your BI tools use.

### Killer feature: Metric Decomposition

Ask "Why did revenue increase?" and falk automatically ranks every dimension by impact:

```bash
$ falk decompose revenue --period month

📊 REVENUE: +$50k (+20%)

🔍 WHERE: Region (70% variance explained)
   🔺 North America: +$35k (+50%)

🧮 HOW: revenue = orders × average_order_value
   → Orders: +1,000 (+10%)
   → AOV: +$5 (+10%)
```

No manual drilling. Instant root cause analysis.

---

## Quick start

```bash
# Clone and install
git clone https://github.com/yourusername/falk.git
cd falk && uv venv && uv sync

# Create a project with sample data
falk init my-project
cd my-project

# Add your API key
cp .env.example .env
# Edit .env: OPENAI_API_KEY=sk-...

# Query
falk query revenue --group-by region
falk decompose revenue --period month

# Web UI
falk chat
# → http://localhost:8000
```

---

## How it works

### 1. Define your semantic layer

```yaml
# semantic_models.yaml
sales_metrics:
  measures:
    revenue:
      expr: _.amount.sum()
      description: "Total revenue (completed orders)"
      synonyms: ["sales", "income"]
      related_metrics: [orders, average_order_value]
```

### 2. Query naturally

**Slack:** "What's our revenue for Acme Corp?"
**CLI:** `falk query revenue --filter "customer=Acme Corp" --json`
**Web:** Type your question, get instant results

### 3. Monitor in production

- **LangFuse** — trace every query, LLM call, and tool invocation
- **Feedback** — 👍/👎 reactions automatically logged
- **Evals** — YAML-based test cases catch regressions

---

## Features

| | |
|---|---|
| **Governed access** | Only approved metrics and dimensions, not raw tables |
| **Consistent numbers** | Same calculation as your BI layer |
| **Business context** | Synonyms, gotchas, and rules built into the schema |
| **Root cause analysis** | Automatic metric decomposition |
| **Multi-interface** | Slack, CLI, web UI, agent skills |
| **Multi-LLM** | OpenAI, Anthropic, Gemini (via Pydantic AI) |
| **Observable** | LangFuse tracing, feedback, evals |

---

## CLI

```bash
falk query revenue -g region           # query metrics
falk decompose revenue --period month  # root cause analysis
falk compare revenue --period week     # period comparison
falk lookup customer --search "acme"   # fuzzy dimension search
falk metrics list                      # discover available metrics
falk chat                              # start web UI
falk slack                             # start Slack bot
falk sync                              # validate config
falk init my-project                   # scaffold new project
```

All commands support `--json` for machine-readable output.

---

## Architecture

```
User (Slack / Web / CLI)
     │
     ▼
Pydantic AI Agent  ← system prompt auto-generated from YAML
     │
     ▼
BSL Semantic Layer  ← governed metric definitions
     │
     ▼
Database (DuckDB)   ← your data
```

**Key principle:** The semantic layer is the contract between humans and AI. Prompts, tools, and responses are all auto-generated from it.

---

## Documentation

📖 **[Full docs →](https://yourusername.github.io/falk/)**

---

## Project structure

```
src/falk/              ← The library (pip-installable)
├── cli.py             # Typer CLI
├── agent.py           # DataAgent core
├── pydantic_agent.py  # Pydantic AI agent + tools
├── prompt.py          # System prompt generation
├── settings.py        # Configuration loading
├── scaffold/          # Templates for falk init
├── tools/             # Query, decompose, charts, exports
└── evals/             # Evaluation framework

app/                   ← Entry points (thin wrappers)
├── web.py             # Web UI (uvicorn)
└── slack.py           # Slack bot (socket mode)
```

---

## Requirements

- Python 3.11+
- OpenAI, Anthropic, or Google API key
- DuckDB (included)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
uv venv && uv sync --extra dev
pytest
ruff check .
# Docs are built via GitHub Actions and hosted on GitHub Pages
```

## License

MIT — see [LICENSE](LICENSE).

---

Built with [Pydantic AI](https://github.com/pydantic/pydantic-ai) · [Boring Semantic Layer](https://github.com/boringdata/boring-semantic-layer) · [DuckDB](https://duckdb.org/) · [LangFuse](https://langfuse.com/)
"# falk" 

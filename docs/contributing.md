# Contributing

## Setup

```bash
git clone https://github.com/Fredehagelund92/Falk.git
cd falk
uv venv
uv sync --extra dev
```

## Project structure

```
src/falk/                         ← The library (pip-installable)
├── cli.py                        # Typer CLI
├── agent.py                      # DataAgent core (BSL models + knowledge)
├── pydantic_agent.py             # Pydantic AI Agent + tool definitions
├── prompt.py                     # System prompt generation
├── settings.py                   # Configuration loading
├── pydantic_agent.py            # Agent + tools
├── scaffold/                     # Templates for falk init
│   ├── RULES.md
│   ├── falk_project.yaml
│   ├── semantic_models_ecommerce.yaml
│   ├── seed_data.py
│   └── knowledge/
├── evals/                        # Evaluation framework
│   ├── cases.py
│   ├── runner.py
│   └── pydantic_adapter.py
└── tools/
    ├── warehouse.py              # Query execution via BSL
    ├── semantic.py               # Semantic model lookups
    ├── calculations.py           # Analytics helpers
    └── charts.py                 # Plotly chart generation

app/                              ← Entry points (thin wrappers)
├── web.py                        # Web UI (uvicorn)
└── slack.py                      # Slack bot (socket mode)

evals/                            ← Evaluation test cases (YAML)
```

## Key principles

- **Library first** — `src/falk/` is a pip-installable package. Everything else is a thin wrapper.
- **Semantic layer driven** — BSL YAML defines all data knowledge.
- **Never invent numbers** — all data comes from the database via tools.
- **Context engineering** — `RULES.md` + `knowledge/` teach the agent about your business.
- **Two config files** — `semantic_models.yaml` (data) + `falk_project.yaml` (technical).
- **Testable** — eval framework catches regressions.

## Running locally

```bash
# Web UI
falk chat

# Docs
mkdocs build  # or mkdocs serve for local preview

# Tests
pytest

# Lint
ruff check .
```

## Deploying docs

```bash
uv run mkdocs gh-deploy
```

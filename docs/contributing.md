# Contributing

## Setup

```bash
git clone https://github.com/Fredehagelund92/Falk.git
cd Falk
uv venv
uv sync --extra dev
```

## Project structure

```
src/falk/                         ← The library (pip-installable)
├── agent.py                      # DataAgent core (BSL models + all data methods)
├── llm/                          # Pydantic AI Agent + tool definitions
├── prompt.py                     # System prompt construction
├── settings.py                   # Configuration loading
├── cli.py                        # Typer CLI
├── validation.py                 # Project validation and testing
├── observability/                # Tracing and feedback
├── backends/                     # Pluggable backends (memory, observability, session)
├── slack/                        # Slack formatting and policy
├── tools/                        # Core functionality (warehouse, semantic, charts)
├── evals/                        # Test framework
└── scaffold/                     # Templates for falk init

app/                              ← Application interfaces (thin wrappers)
├── web.py                        # Web UI (uvicorn)
├── slack.py                      # Slack bot (socket mode)
└── mcp.py                        # MCP server (FastMCP)
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
npm run start

# Tests
pytest

# Lint
ruff check .
```

## Deploying docs

Docs are built and deployed via GitHub Actions when you push to `main`. See `.github/workflows/docs.yml`.

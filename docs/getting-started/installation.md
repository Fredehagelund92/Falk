# Installation

## Prerequisites

- **Python 3.11 or higher**
- **PostgreSQL** for session storage (Falk creates schema and tables automatically)
- **API key** for OpenAI, Anthropic Claude, or Google Gemini
- (Recommended) [uv](https://github.com/astral-sh/uv) for fast package management

## Install from Source

```bash
# Clone the repository
git clone https://github.com/Fredehagelund92/Falk.git
cd falk

# Set up virtual environment
uv venv && uv sync

# Or with pip
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## Install from PyPI

```bash
pip install falk
```

## Verify Installation

```bash
# Check CLI is available
falk --help

# Create a project
falk init my-project
cd my-project

# Configure environment
cp .env.example .env
# Edit .env: set POSTGRES_URL and your LLM API key (e.g. OPENAI_API_KEY)

# Validate
falk validate --fast

# Query through one of the interfaces
falk chat
# or
falk mcp
```

## Configure LLM Provider

falk supports multiple LLM providers via Pydantic AI. Set your preferred provider in `.env`:

```bash
# OpenAI (default)
OPENAI_API_KEY=sk-...

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
GOOGLE_API_KEY=...
```

See [LLM Provider Configuration](../configuration/llm-providers.md) for details.

## Optional: Logfire Observability

For production monitoring, add Logfire Cloud:

```bash
# .env
LOGFIRE_TOKEN=...
```

Run `logfire auth` and `logfire projects new` first. All queries, LLM calls, and user feedback will be traced automatically.

## Troubleshooting

### "falk: command not found"

Ensure the virtual environment is activated:

```bash
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
pip install -e .
```

### "No metrics found"

Check that:

1. `semantic_models.yaml` exists and is valid YAML
2. The database path in `.env` is correct
3. Table names in `semantic_models.yaml` match your database

### "API key error"

Verify your API key is set in `.env` and is valid.

## Next Steps

- [Quick Start](./quickstart.md) — Build your first project
- [Semantic Models](../configuration/semantic-models.md) — Define your metrics
- [CLI Reference](../cli-reference.md) — All available commands

# CLI Overview

The `falk` CLI is the primary interface for querying, exploring, and running falk.

Use `--json` on most commands to get machine-readable output for agent skills and automation.

## Getting started

```bash
# After installing (pip install -e . or uv sync)
falk --help
```

## Commands

### Data

| Command | What it does |
|---------|-------------|
| `falk query` | Query a metric from the warehouse |
| `falk decompose` | Root cause analysis — explain *why* a metric changed |
| `falk lookup` | Fuzzy-search dimension values |
| `falk compare` | Compare metrics across periods |
| `falk export` | Export results to CSV or JSON |

### Discovery

| Command | What it does |
|---------|-------------|
| `falk metrics list` | List all available metrics |
| `falk metrics describe` | Get details about a specific metric |
| `falk dimensions list` | List all available dimensions |
| `falk dimensions describe` | Get details about a specific dimension |
| `falk config` | Show current configuration |

### Project

| Command | What it does |
|---------|-------------|
| `falk init` | Scaffold a new falk project |
| `falk sync` | Validate configuration |
| `falk evals` | Run evaluation test cases |

### Servers

| Command | What it does |
|---------|-------------|
| `falk chat` | Start the web UI (default: port 8000) |
| `falk slack` | Start the Slack bot |

## Examples

```bash
# Query revenue grouped by region
falk query revenue -g region --order desc --limit 10

# Why did revenue change?
falk decompose revenue --period month

# Machine-readable output
falk query revenue -g region --json

# Start the web UI
falk chat

# Validate everything works
falk sync
```

For full details on every command and option, see the [CLI Reference](cli-reference.md).

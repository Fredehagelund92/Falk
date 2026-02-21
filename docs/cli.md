# CLI Overview

The `falk` CLI manages projects, runs tests, and starts servers.

**For data queries and agent interactions**, use:
- **MCP server** (`falk mcp`) - Connect from Cursor, Claude Desktop, or any MCP client
- **Web UI** (`falk chat`) - Interactive web interface
- **Slack bot** (`falk slack`) - Team collaboration

## Getting started

```bash
# After installing
pip install falk

# Or from source
git clone https://github.com/Fredehagelund92/Falk.git
cd Falk
uv sync
```

## Commands

### Project Management

| Command | What it does |
|---------|-------------|
| `falk init` | Create a new project with sample data |
| `falk validate` | Validate configuration, models, and optional runtime checks |
| `falk test` | Run eval cases from `evals/` |
| `falk config` | Show current project configuration |

### Servers

| Command | What it does |
|---------|-------------|
| `falk mcp` | Start MCP server (for Cursor, Claude Desktop) |
| `falk chat` | Start web UI (default: port 8000) |
| `falk slack` | Start Slack bot |

## Examples

```bash
# Create a new project
falk init my-project
cd my-project

# Validate configuration
falk validate --fast

# Start MCP server (connect from Cursor)
falk mcp

# Or start web UI for interactive queries
falk chat

# Or start Slack bot for team collaboration
falk slack
```

For full details on every command and option, see the [CLI Reference](cli-reference.md).

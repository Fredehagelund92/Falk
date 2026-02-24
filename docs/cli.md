# CLI Overview

The `falk` CLI manages projects, runs tests, and starts servers.

**For data queries and agent interactions**, use:

- **MCP server** (`falk mcp`) — Connect from Cursor, Claude Desktop, or any MCP client
- **Web UI** (`falk chat`) — Interactive web interface
- **Slack bot** (`falk slack`) — Team collaboration

## Commands

### Project management

| Command | What it does |
|---------|--------------|
| `falk init` | Create a new project with sample data |
| `falk validate` | Validate configuration, models, and optional runtime checks |
| `falk test` | Run eval cases from `evals/` |
| `falk config` | Show current project configuration |

### Servers

| Command | What it does |
|---------|--------------|
| `falk mcp` | Start MCP server (for Cursor, Claude Desktop) |
| `falk chat` | Start web UI (default: port 8000) |
| `falk slack` | Start Slack bot |

## Quick example

```bash
falk init my-project
cd my-project

falk validate --fast

# Start querying
falk mcp      # Connect from Cursor
falk chat     # Web UI
falk slack   # Team collaboration
```

For full details on every command and option, see the [CLI Reference](/cli-reference).

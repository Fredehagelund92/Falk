# Using falk with MCP

falk exposes governed metric queries through the **Model Context Protocol (MCP)**, so you can query your data warehouse safely from Cursor, Claude Desktop, or any MCP client.

## What is MCP?

The Model Context Protocol is a standard way for AI applications to connect to external tools. falk uses **FastMCP** from the Pydantic AI ecosystem.

With falk's MCP server you can:

- Query falk from **Cursor** while coding
- Ask falk questions in **Claude Desktop**
- Build custom agents that use falk as a data tool
- Chain falk with other MCP servers

## Start the MCP server

```bash
# Stdio mode (default) — for local Cursor/Claude
falk mcp

# HTTP mode — for shared server deployments
falk mcp --transport http --host 127.0.0.1 --port 8000
```

The server loads your project config, connects to your semantic models, and exposes tools for querying metrics. **Logfire** is optional; if `LOGFIRE_TOKEN` is not set, the server runs without tracing.

## Available tools

### Discovery

- **`list_catalog`** — List metrics and/or dimensions
- **`suggest_date_range`** — Get common date ranges (last_7_days, this_month, etc.)
- **`describe_metric`** — Full description of a metric
- **`describe_model`** — Full description of a semantic model
- **`describe_dimension`** — Full description of a dimension
- **`lookup_dimension_values`** — Look up values for a dimension
- **`disambiguate`** — Find close metric/dimension matches

### Querying

- **`query_metric`** — Query metrics with grouping, filtering, period comparison, and share breakdown

## Connect from Cursor

1. Open Cursor settings and add falk as an MCP server:

```json
{
  "mcpServers": {
    "falk": {
      "command": "falk",
      "args": ["mcp"],
      "cwd": "/path/to/your/falk-project"
    }
  }
}
```

:::tip
`cwd` must point at your falk project root (where `falk_project.yaml` and `.env` live).
:::

2. Query naturally in Cursor: "Show me revenue by region", "Compare revenue this month vs last"

## Connect from Claude Desktop

1. Add falk to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "falk": {
      "command": "falk",
      "args": ["mcp"],
      "cwd": "/path/to/your/falk-project"
    }
  }
}
```

2. Restart Claude Desktop.

3. Ask questions: "List available metrics", "Show revenue trends by product", "Why did sales drop last quarter?"

## Shared server (HTTP)

For deployments where multiple users connect to one MCP server:

```bash
# Bind to all interfaces (use only on trusted networks)
falk mcp --transport http --host 0.0.0.0 --port 8000

# Bind to localhost only (for reverse proxy)
falk mcp --transport http --host 127.0.0.1 --port 8000
```

:::caution
When using `--host 0.0.0.0`, the server is reachable from the network. Use a reverse proxy (nginx, Caddy) with TLS and authentication in production.
:::

Clients connect to `http://<server>:8000/mcp`.

## Use from other agents

Connect to falk's MCP server from your own Pydantic AI agent:

```python
from pydantic_ai import Agent
from pydantic_ai.toolsets.fastmcp import FastMCPToolset

falk_toolset = FastMCPToolset({
    'mcpServers': {
        'falk': {
            'command': 'falk',
            'args': ['mcp'],
            'cwd': '/path/to/your/falk-project'
        }
    }
})

agent = Agent('openai:gpt-4', toolsets=[falk_toolset])
result = await agent.run("What's our revenue by region?")
print(result.output)
```

## Next steps

- [Agent Tools](/concepts/tools) — Complete list of MCP tools
- [Web UI](/deployment/web-ui) — Interactive chat interface
- [Slack Bot](/deployment/slack) — Team collaboration interface

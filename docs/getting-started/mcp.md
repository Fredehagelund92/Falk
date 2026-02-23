# Using falk with MCP Clients

falk exposes its governed metric queries through the **Model Context Protocol (MCP)**, allowing any MCP client to query your data warehouse safely.

## What is MCP?

The Model Context Protocol is a standardized way for AI applications to connect to external tools and services. falk uses **FastMCP**, a higher-level MCP framework from the Pydantic AI ecosystem that provides a simpler, more Pythonic API.

With falk's MCP server, you can:

- Query falk from **Cursor** while coding
- Ask falk questions in **Claude Desktop**
- Build custom agents that use falk's MCP server as a data tool
- Chain falk with other MCP servers for complex workflows

## Starting the MCP Server

```bash
# Stdio mode (default) — for local Cursor/Claude
falk mcp

# HTTP mode — for shared server deployments
falk mcp --transport http --host 127.0.0.1 --port 8000
```

The MCP server will:
1. Load your project configuration from `falk_project.yaml`
2. Connect to your semantic models
3. Expose tools for querying metrics

**Logfire** (observability) is optional. If `LOGFIRE_TOKEN` is not set, the server runs without tracing; startup is never blocked.

## Available MCP Tools

falk exposes these tools via MCP:

### Discovery & Metadata

- **`list_catalog(entity_type)`** — List metrics and/or dimensions (entity_type: metric \| dimension \| both)
- **`suggest_date_range(period)`** — Get common date ranges (last_7_days, this_month, etc.)
- **`describe_metric`** — Get full description of a metric
- **`describe_model`** — Get full description of a semantic model
- **`describe_dimension`** — Get full description of a dimension
- **`lookup_dimension_values`** — Look up actual values for a dimension
- **`disambiguate(entity_type, concept)`** — Find close metric/dimension matches for clarification

### Querying

- **`query_metric`** — Query metrics with optional grouping, filtering, compare_period, include_share

### Tool Name Mapping (Agent vs MCP)

- Agent tool name: `lookup_values`
- MCP tool name: `lookup_dimension_values`
- These are equivalent capabilities exposed through different interfaces.

## Connecting from Cursor (stdio)

1. **Configure Cursor** to connect to falk (Cursor spawns the server automatically):
   
   Open Cursor settings and add falk as an MCP server:
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

   **Important:** `cwd` must point at your falk project root (where `falk_project.yaml` and `.env` live). Cursor uses this as the working directory when spawning the process.

2. **Query naturally in Cursor:**
   ```
   You: "Show me revenue by region"
   → Cursor calls falk's query_metric tool
   
   You: "Compare revenue this month vs last"
   → Cursor calls falk's query_metric with compare_period="month"
   ```

## Connecting from Claude Desktop

1. **Configure Claude Desktop** in `claude_desktop_config.json`:
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

2. **Restart Claude Desktop** to load the new MCP server. Ensure `cwd` points at your falk project root.

3. **Ask questions in Claude Desktop:**
   - "List available metrics"
   - "Show revenue trends by product"
   - "Why did sales drop last quarter?"

## Shared Server (HTTP) Deployment

For company deployments where multiple users connect to one MCP server:

```bash
# Bind to all interfaces (use only on trusted networks)
falk mcp --transport http --host 0.0.0.0 --port 8000

# Bind to localhost only (for local reverse proxy)
falk mcp --transport http --host 127.0.0.1 --port 8000
```

**Security:** When using `--host 0.0.0.0`, the server is reachable from the network. Use a reverse proxy (nginx, Caddy) with TLS and authentication in production. Avoid exposing the MCP endpoint directly to the internet without access controls.

Clients that support HTTP transport can connect to `http://<server>:8000/mcp`.

## Using from Other Agents

If you're building your own Pydantic AI agent, you can connect to falk's MCP server using FastMCP:

```python
from pydantic_ai import Agent
from pydantic_ai.toolsets.fastmcp import FastMCPToolset

# Create toolset from falk MCP server
falk_toolset = FastMCPToolset({
    'mcpServers': {
        'falk': {
            'command': 'falk',
            'args': ['mcp'],
            'cwd': '/path/to/your/falk-project'
        }
    }
})

# Create agent with falk toolset
agent = Agent('openai:gpt-4', toolsets=[falk_toolset])

# Now your agent can use falk's tools
result = await agent.run("What's our revenue by region?")
print(result.output)
```

## Architecture

```
┌─────────────────┐
│  Cursor / IDE   │────┐
└─────────────────┘    │
                       │
┌─────────────────┐    │    ┌──────────────┐
│ Claude Desktop  │────┼───▶│  falk MCP    │
└─────────────────┘    │    │   Server     │
                       │    └──────┬───────┘
┌─────────────────┐    │           │
│  Custom Agent   │────┘           │
└─────────────────┘                │
                                   ▼
                          ┌─────────────────┐
                          │   DataAgent     │
                          │ (Semantic Layer)│
                          └────────┬────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │   Warehouse     │
                          │ (DuckDB/SF/BQ)  │
                          └─────────────────┘
```

## Tool Examples

### Query a metric

```python
# MCP client calls:
query_metric(
    metrics=["revenue"],
    dimensions=["region"],
    time_grain="month",
    limit=10
)

# Returns:
{
    "rows": [
        {"region": "US", "revenue": 100000},
        {"region": "EU", "revenue": 85000},
        ...
    ],
    "row_count": 10,
    "metrics": ["revenue"],
    "model": "sales_metrics"
}
```

### Query with filters

Use structured filters:

```python
# Simple equality
query_metric(
    metrics=["revenue"],
    dimensions=["product_category"],
    filters=[{"field": "region", "op": "=", "value": "US"}],
)

# Comparisons
query_metric(
    metrics=["revenue"],
    dimensions=["region"],
    filters=[{"field": "date", "op": ">=", "value": "2024-01-01"}],
)

# Multiple conditions with AND
query_metric(
    metrics=["revenue"],
    dimensions=["product_category"],
    filters=[
        {"field": "region", "op": "=", "value": "US"},
        {"field": "date", "op": ">=", "value": "2024-01-01"},
    ],
)

# IN clause for multiple values
query_metric(
    metrics=["revenue"],
    dimensions=["product_category"],
    filters=[{"field": "region", "op": "IN", "value": ["US", "EU", "APAC"]}],
)
```

### Compare periods

Use `query_metric` with `compare_period="week"|"month"|"quarter"` to compare a metric across current vs previous period.

## Benefits of MCP

1. **Standardized interface** — Same tools work in Cursor, Claude, custom agents
2. **Governed access** — All queries go through your semantic layer
3. **Composable** — Chain falk with other MCP servers
4. **Secure** — MCP server runs locally with your credentials
5. **Type-safe** — Tool schemas ensure valid requests

## Next Steps

- [MCP Configuration](../configuration/mcp.md) — Advanced MCP server settings
- [Tool Reference](../reference/mcp-tools.md) — Complete list of MCP tools
- [CLI Chat](../deployment/web-ui.md) — Interactive terminal interface
- [Slack Bot](../deployment/slack.md) — Team collaboration interface

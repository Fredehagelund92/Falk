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
# Start the MCP server
falk mcp
```

The MCP server will:
1. Load your project configuration from `falk_project.yaml`
2. Connect to your semantic models
3. Expose tools for querying metrics

## Available MCP Tools

falk exposes these tools via MCP:

### Discovery & Metadata

- **`list_metrics`** — List all available metrics grouped by semantic model
- **`list_dimensions`** — List all available dimensions with display names
- **`describe_metric`** — Get full description of a metric
- **`describe_model`** — Get full description of a semantic model
- **`describe_dimension`** — Get full description of a dimension
- **`lookup_dimension_values`** — Look up actual values for a dimension

### Querying

- **`query_metric`** — Query a metric with optional grouping and WHERE filtering
- **`compare_periods`** — Compare metric across time periods
- **`decompose_metric`** — Decompose metric change to find root causes (variance analysis)

### Visualization

- **`generate_chart`** — Generate bar/line/pie chart from query data
- **`suggest_chart`** — Suggest best chart type for query results

## Connecting from Cursor

1. **Start the MCP server:**
   ```bash
   falk mcp
   ```

2. **Configure Cursor** to connect to falk:
   
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

3. **Query naturally in Cursor:**
   ```
   You: "Show me revenue by region"
   → Cursor calls falk's query_metric tool
   
   You: "Why did revenue increase this month?"
   → Cursor calls falk's decompose_metric tool
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

2. **Restart Claude Desktop** to load the new MCP server

3. **Ask questions in Claude Desktop:**
   - "List available metrics"
   - "Show revenue trends by product"
   - "Why did sales drop last quarter?"

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
    metric="revenue",
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
    "metric": "revenue",
    "model": "sales_metrics"
}
```

### Query with filters

The `where` parameter supports SQL-like filtering:

```python
# Simple equality
query_metric(
    metric="revenue",
    dimensions=["product_category"],
    where="region = 'US'"
)

# Comparisons
query_metric(
    metric="revenue",
    dimensions=["region"],
    where="date >= '2024-01-01'"
)

# Multiple conditions with AND
query_metric(
    metric="revenue",
    dimensions=["product_category"],
    where="region = 'US' AND date >= '2024-01-01'"
)

# IN clause for multiple values
query_metric(
    metric="revenue",
    dimensions=["product_category"],
    where="region IN ('US', 'EU', 'APAC')"
)
```

**Supported operators:**
- `=` — Equality
- `>`, `>=`, `<`, `<=` — Comparisons
- `IN (...)` — List membership
- `AND` — Multiple conditions

### Decompose a metric change

```python
# MCP client calls:
decompose_metric(
    metric="revenue",
    period="month"
)

# Returns:
{
    "metric": "revenue",
    "current_value": 150000,
    "previous_value": 100000,
    "change": 50000,
    "change_pct": 50.0,
    "drivers": [
        {
            "dimension": "region",
            "dimension_value": "North America",
            "contribution": 0.70,
            "change": 35000
        },
        ...
    ]
}
```

## Benefits of MCP

1. **Standardized interface** — Same tools work in Cursor, Claude, custom agents
2. **Governed access** — All queries go through your semantic layer
3. **Composable** — Chain falk with other MCP servers
4. **Secure** — MCP server runs locally with your credentials
5. **Type-safe** — Tool schemas ensure valid requests

## Next Steps

- [MCP Configuration](../configuration/mcp.md) — Advanced MCP server settings
- [Tool Reference](../reference/mcp-tools.md) — Complete list of MCP tools
- [Web UI](../deployment/web-ui.md) — Alternative conversational interface
- [Slack Bot](../deployment/slack.md) — Team collaboration interface

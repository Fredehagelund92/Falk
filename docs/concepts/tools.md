# Agent Tools

The agent has tools the LLM can call. Users don't see tool names — they just ask questions in natural language.

## Custom Tool Extensions

You can add project-specific Python tools in your falk project and register them via `falk_project.yaml`. Tool logic stays in Python; YAML only registers which modules to load.

### Configure

In `falk_project.yaml` under `agent`:

```yaml
agent:
  extensions:
    tools:
      - module: project_tools.customer_health
      - module: project_tools.forecasting
      - module: project_tools.alerts
        enabled: false   # optional: disable without removing
```

### Implement

Create a Python module in your project (e.g. `project_tools/customer_health.py`) that exports a `FunctionToolset` instance as `toolset`, `data_tools`, or `tools`:

```python
from pydantic_ai import FunctionToolset, RunContext
from falk.agent import DataAgent

toolset = FunctionToolset()

@toolset.tool
def customer_health_score(ctx: RunContext[DataAgent], customer_id: str) -> dict:
    """Compute health score for a customer."""
    # Use ctx.deps for DataAgent (warehouse, metrics, etc.)
    agent = ctx.deps
    # ... your logic ...
    return {"score": 0.85, "trend": "up"}
```

### Runtime behavior

- Custom tools are loaded at startup when the agent or MCP server starts.
- Invalid or missing modules log warnings and are skipped; built-in tools remain available.
- Tools are exposed in both the agent (chat, web, Slack) and the MCP server.

### Testing

1. **Unit tests**: Call each tool function directly with a mock `ctx` (e.g. `ctx.deps = DataAgent()`).
2. **Integration tests**: Run `agent.run_sync("question")` and assert the model uses the right tool.
3. **Evals**: Add `evals/` cases for user phrasing that should trigger your custom tools.

See [Project Config](../configuration/agent.md) for the full config schema.

## Data Querying

| Tool | What it does |
|------|--------------|
| `query_metric` | Query metrics with optional group_by, filters, time_grain, order, limit, compare_period, include_share |
| `lookup_values` | Find actual values in a dimension (fuzzy search) |

### `query_metric` — The main tool

```python
query_metric(
    metrics=["revenue"],
    group_by=["customer"],
    time_grain="month",
    filters=[{"field": "customer", "op": "=", "value": "Acme Corp"}],
    order="desc",
    limit=10,
    compare_period="month",   # optional: week | month | quarter
    include_share=True,       # optional: add share_pct column
)
```

## Export

| Tool | What it does |
|------|--------------|
| `export(format)` | Export last result (format: csv \| excel \| sheets) |
| `generate_chart` | Generate a Plotly chart (bar, line, pie) |

In Slack, exported files are uploaded directly to the channel.

## Date Ranges

| Tool | What it does |
|------|--------------|
| `suggest_date_range(period)` | Get date range for common periods: yesterday, today, last_7_days, last_30_days, this_week, this_month, last_month, this_quarter |

## Metadata / Discovery

| Tool | What it does |
|------|--------------|
| `list_catalog(entity_type)` | List metrics and/or dimensions (entity_type: metric \| dimension \| both) |
| `describe_metric` | Get metric details (description, dimensions, time grains) |
| `describe_model` | Get full semantic model description |
| `describe_dimension` | Get dimension meaning (helps with disambiguation) |
| `disambiguate(entity_type, concept)` | Find metrics/dimensions matching a concept; use when the user's request is ambiguous to ask a clarification question |

## Interface Naming Note

- Agent interface tool: `lookup_values(dimension, search)`
- MCP interface tool: `lookup_dimension_values(dimension, search)`
- They expose the same lookup capability with interface-specific names.

## Chart Auto-Detection

When the user asks for a chart without specifying a type, the agent picks the best one:

| Data shape | Chart type |
|------------|------------|
| Time dimension present | Line chart |
| 2–8 categories | Pie chart |
| 9+ categories | Bar chart |

Users can override: "show me a bar chart" or "make it a pie chart".

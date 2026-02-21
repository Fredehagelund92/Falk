# Agent Tools

The agent has tools the LLM can call. Users don't see tool names — they just ask questions in natural language.

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

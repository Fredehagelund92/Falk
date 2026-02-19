# Agent Tools

The agent has tools the LLM can call. Users don't see tool names — they just ask questions in natural language.

## Data Querying

| Tool | What it does |
|------|--------------|
| `query_metric` | Query a metric with optional group_by, filters, time_grain, order, limit |
| `lookup_values` | Find actual values in a dimension (fuzzy search) |

### `query_metric` — The main tool

```python
query_metric(
    metric="revenue",
    group_by=["customer"],
    time_grain="month",
    filters=[{"dimension": "customer", "op": "=", "value": "Acme Corp"}],
    order="desc",
    limit=10
)
```

## Analytics

| Tool | What it does |
|------|--------------|
| `compare_periods` | Compare this vs last week/month/quarter |
| `compute_share` | Show % breakdown from the last query |

## Export

| Tool | What it does |
|------|--------------|
| `export(format)` | Export last result (format: csv \| excel \| sheets) |
| `generate_chart` | Generate a Plotly chart (bar, line, pie) |

In Slack, exported files are uploaded directly to the channel.

## Metadata / Discovery

| Tool | What it does |
|------|--------------|
| `list_metrics` | See all available metrics |
| `list_dimensions` | See available dimensions (filterable by domain) |
| `describe_metric` | Get metric details (description, dimensions, time grains) |
| `describe_model` | Get full semantic model description |
| `describe_dimension` | Get dimension meaning (helps with disambiguation) |
| `disambiguate(entity_type, concept)` | Find metrics/dimensions matching a concept; use when the user's request is ambiguous to ask a clarification question |

## Chart Auto-Detection

When the user asks for a chart without specifying a type, the agent picks the best one:

| Data shape | Chart type |
|------------|------------|
| Time dimension present | Line chart |
| 2–8 categories | Pie chart |
| 9+ categories | Bar chart |

Users can override: "show me a bar chart" or "make it a pie chart".

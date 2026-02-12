# Metric Decomposition

> Automatic root cause analysis for metric changes.

When you ask "Why did revenue increase?", falk automatically analyzes every dimension, ranks them by impact, and shows what's driving the change. No manual drilling.

## How it works

```bash
falk decompose revenue --period month
```

```
📊 REVENUE DECOMPOSITION (month over month)
============================================================

Overall Change: +$50,000.00 (+20.0%)
  Current:      $300,000.00
  Previous:     $250,000.00

🔍 Dimension Impact Ranking:
   1. region                 70.0% variance explained ← Main driver
   2. product                45.0% variance explained
   3. customer_segment       30.0% variance explained

📈 Breakdown by REGION:
   🔺 North America          +$35,000 (+50%) —  70% of total change
   🔺 Latin America          +$20,000 (+40%) —  40% of total change
   🔻 Asia                   -$10,000 (-10%) — -20% of total change
```

**What happened:**

1. Revenue increased by $50k (+20%)
2. Region explains 70% of the variance (the main driver)
3. North America drove most of the growth (+$35k)
4. Asia declined, but was offset by other regions

## Usage

### CLI

```bash
falk decompose revenue
falk decompose orders --period week
falk decompose revenue --filter "region=North America"
falk decompose revenue --json   # for agent skills
```

### As an agent tool

When users ask "why" questions in Slack or the web UI, the agent calls `decompose_metric()` automatically and presents the breakdown in natural language.

### Python API

```python
from falk.tools.warehouse import decompose_metric_change
from falk.agent import DataAgent

agent = DataAgent()
result = decompose_metric_change(
    core=agent.core,
    metric="revenue",
    period="month",
)

if result.ok:
    print(f"Top driver: {result.top_dimension}")
    for item in result.top_dimension_breakdown[:5]:
        print(f"  {item['dimension_value']}: {item['variance_pct']:+.1f}%")
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `metric` | str | *required* | Metric name (e.g., "revenue") |
| `period` | str | `"month"` | `"week"`, `"month"`, or `"quarter"` |
| `dimensions` | list | `None` | Dimensions to analyze (default: all) |
| `filters` | dict | `None` | Optional filters |
| `max_breakdown_items` | int | `10` | Max items in breakdown |

## How variance is calculated

For each dimension, falk calculates:

1. **Deltas per value** — how much each dimension value changed
2. **Total movement** — sum of absolute deltas
3. **Variance %** — `total_movement / abs(total_delta) × 100`

Variance can exceed 100% when changes in opposite directions offset each other. For example: Region A up $150k, Region B down $50k, total change $100k → variance = 200%. This means the dimension has high internal movement, making it a strong driver.

## Related metrics

If your metric has `related_metrics` defined in the semantic model, the agent also explains **how** the change happened (not just where):

```
Revenue: +20%
├── WHERE (dimensions): North America drove 70%
└── HOW (related metrics):
    → Orders: +10% — contributed $25k
    → AOV: +10% — contributed $25k
```

See [Metric Relationships](../configuration/metric-relationships.md) for configuration.

## Best practices

1. **Start broad, then narrow** — decompose first, then filter to the top driver
2. **Choose the right period** — week for ops metrics, month for business, quarter for strategic
3. **Combine with queries** — after finding the driver, query for more detail

```bash
# 1. Find the driver
falk decompose revenue --period month
# → Region (North America +70%)

# 2. Drill in
falk query revenue --group-by region,product --filter "region=North America"
```

## Limitations

- **Single-level drill-down** — currently drills into the top dimension only
- **Requires historical data** — needs data for both current and previous period
- **Best for additive metrics** — revenue, orders, clicks. Ratios (conversion rate) need different interpretation

## Related

- [Metric Relationships](../configuration/metric-relationships.md) — define how metrics relate
- [Agent Tools](./tools.md) — all available tools
- [CLI Reference](../cli-reference.md) — command reference

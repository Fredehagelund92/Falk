# Metric Relationships

> Help the agent answer "why" questions by defining how metrics relate.

When users ask "Why did revenue increase?", they want to understand:
- **WHERE** the change happened (dimensions → handled by [decomposition](../concepts/metric-decomposition.md))
- **HOW** the change happened (underlying metrics → handled by relationships)

## Configuration

Add `related_metrics` and optionally `formula` to your metrics in `semantic_models.yaml`:

```yaml
measures:
  revenue:
    expr: _.revenue.sum()
    description: "Total revenue"
    related_metrics:
      - orders
      - average_order_value
    formula: "orders × average_order_value"

  orders:
    expr: _.orders.sum()
    description: "Number of orders"

  average_order_value:
    expr: _.revenue.sum() / _.orders.sum()
    description: "Average value per order"
```

The agent reads `related_metrics`, queries them for the same period, and presents the complete picture.

## Examples

### E-commerce

```yaml
revenue:
  related_metrics: [orders, average_order_value]
  formula: "orders × average_order_value"

profit:
  related_metrics: [revenue, costs]
  formula: "revenue - costs"
```

### SaaS

```yaml
mrr:
  related_metrics: [active_subscriptions, arpu]
  formula: "active_subscriptions × arpu"

net_new_mrr:
  related_metrics: [new_mrr, churned_mrr, expansion_mrr]
  formula: "new_mrr - churned_mrr + expansion_mrr"
```

### Multi-model business

For businesses where drivers vary by dimension (e.g., subscription vs advertising), use descriptions:

```yaml
revenue:
  description: |
    Revenue drivers vary by site:
    - Site A (subscription): subscribers × price
    - Site B (advertising): impressions × cpm
    - Site C (ecommerce): transactions × aov
  related_metrics:
    - active_subscribers
    - subscription_price
    - total_impressions
    - cpm
    - transactions
    - average_order_value
```

The agent reads the description and adapts its analysis to the relevant segment.

## How the agent uses it

When a user asks "Why did revenue increase?":

1. **Decompose by dimensions** — which regions/products/segments drove the change
2. **Check `related_metrics`** — query orders and AOV for the same period
3. **Present both**: WHERE (dimensions) and HOW (related metrics)

No additional prompting needed — just define the relationships in your semantic models.

## Best practices

- **Start simple** — begin with the obvious relationships (revenue = orders × AOV)
- **Keep lists short** — 2–4 related metrics per parent; too many makes output noisy
- **Add formulas** — optional but helpful for the agent and for documentation
- **Don't overthink it** — focus on metrics users frequently ask "why" about

## Related

- [Metric Decomposition](../concepts/metric-decomposition.md) — automatic root cause analysis
- [Semantic Models](./semantic-models.md) — full configuration guide

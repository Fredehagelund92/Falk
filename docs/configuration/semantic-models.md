# Semantic Models

`semantic_models.yaml` (in project root) is the **single source of truth** for the data agent. It defines what tables, metrics, and dimensions exist using the [Boring Semantic Layer (BSL)](https://github.com/boringdata/boring-semantic-layer) YAML format.

## Format

```yaml
model_name:
  table: duckdb_table_name
  database: [schema_name]          # optional
  description: "What this model represents"
  dimensions:
    dimension_name:
      display_name: "Dimension Name"  # business-friendly label (optional)
      expr: _.column_name           # ibis deferred expression
      description: "What this dimension means"
      is_time_dimension: true       # mark date/time columns
      is_entity: true               # mark entity columns (for fuzzy matching)
      data_domain: "sales"          # optional: core, sales, finance, etc.
      synonyms: ["alias1", "alias2"]  # optional: terms your team uses
      gotchas: "Known data quirk"    # optional: data quality warning
  measures:
    measure_name:
      expr: _.column.sum()          # ibis aggregation expression
      description: "What this metric measures"
      synonyms: ["alias1", "alias2"]  # optional: terms your team uses
      gotchas: "Known data quirk"    # optional: data quality warning
```

## Display Names

Use `display_name` to provide business-friendly labels for dimensions:

```yaml
dimensions:
  customer_segment:
    display_name: "Customer Segment"  # Shows as "Customer Segment" not "customer_segment"
    expr: _.customer_segment
    description: "Customer segment (Enterprise, SMB, Consumer)"
  
  product_category:
    display_name: "Product Category"
    expr: _.product_category
    description: "Product category (Electronics, Clothing, etc.)"
```

**Best practice:** Always add `display_name` as the first property (before `expr`) for readability.

**How it appears:**
- With `display_name`: **"Customer Segment"** (`customer_segment`)
- Without `display_name`: **"customer_segment"**

The technical name is still used for SQL queries, but users see the friendly label.

## Synonyms

Add `synonyms` to any metric or dimension so the agent understands your team's everyday terminology:

```yaml
measures:
  revenue:
    expr: _.revenue.sum()
    description: "Total revenue in USD"
    synonyms: ["sales", "income", "turnover"]

dimensions:
  region:
    expr: _.region
    description: "Sales region"
    synonyms: ["territory", "area", "market"]
```

When a user says "sales" or "turnover", the agent automatically maps it to the `revenue` metric.

Synonyms are:

- **Version-controlled** — reviewed via PR, shared across the team
- **Injected into the system prompt** — the LLM sees them on every query
- **Low maintenance** — add them once, they work forever

## Example

```yaml
sales_metrics:
  table: sales_fact
  database: [main]
  description: "E-commerce sales data with revenue, orders, and customer metrics"

  dimensions:
    date:
      display_name: "Date"
      expr: _.date
      description: "Transaction date"
      is_time_dimension: true

    region:
      display_name: "Region"
      expr: _.region
      description: "Sales region (US, EU, APAC, LATAM)"
      synonyms: ["territory", "area", "market"]
      gotchas: "LATAM data only available from 2025-06 onwards"

  measures:
    revenue:
      expr: _.revenue.sum()
      description: "Total revenue in USD"
      synonyms: ["sales", "income", "turnover"]
      gotchas: "Revenue has a 48-hour reporting delay"
```

When someone asks "what was our revenue yesterday?", the agent will mention the delay. When someone queries LATAM data before June 2025, it'll flag the availability gap.

For global data quality notes, document them in `knowledge/gotchas.md` (detailed) or `falk_project.yaml` `agent.gotchas` (one-line reminders). See [Context](/concepts/context).

## What gets auto-generated

From this YAML, the agent automatically creates:

- **System prompt** — model summaries, key concepts, dimension glossary, vocabulary, **gotchas**
- **Tool behavior** — which metrics/dimensions are queryable
- **Entity resolution** — fuzzy matching on `is_entity` dimensions
- **Disambiguation hints** — for similar dimensions (e.g., different "country" fields)

## Tips

:::tip Descriptions matter
Write clear, concise descriptions. They appear in the system prompt and help the LLM understand your data. First sentence should explain the concept; examples help a lot.
:::

:::tip Use `synonyms`
Add synonyms for any metric or dimension where your team uses different terminology than the data model. This is the easiest way to improve the agent's understanding.
:::

:::tip Use `gotchas`
Add gotchas for data quirks your team keeps running into — delays, coverage gaps, known issues. The agent will warn users proactively instead of returning confusing results.
:::

:::tip Use `data_domain`
Adding `data_domain: "sales"` to dimensions helps the agent group related concepts and can be used to filter `list_dimensions(domain="sales")`.
:::

:::tip Mark time dimensions
Always set `is_time_dimension: true` on date columns — this enables time-grain queries ("by day", "by month") and period comparisons.
:::

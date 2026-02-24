# WHERE Clause Syntax

falk's MCP `query_metric` tool supports SQL-like WHERE clauses for filtering query results.

## Supported syntax

### Equality

```sql
region = 'US'
customer_segment = 'Enterprise'
```

Converts to: `{"region": "US"}`

### Comparisons

```sql
date >= '2024-01-01'
revenue > 100000
date <= '2024-12-31'
```

Converts to: `{"date": {"gte": "2024-01-01"}}`, `{"revenue": {"gt": 100000}}`, etc.

### Multiple conditions (AND)

```sql
region = 'US' AND date >= '2024-01-01'
region = 'US' AND date >= '2024-01-01' AND date <= '2024-12-31'
```

### IN clause

```sql
region IN ('US', 'EU', 'APAC')
customer_segment IN ('Enterprise', 'SMB')
```

Converts to: `{"region": ["US", "EU", "APAC"]}`

## Supported operators

| Operator | BSL format | Example |
|----------|------------|---------|
| `=` | Direct value | `region = 'US'` |
| `>` | `{"gt": value}` | `revenue > 1000` |
| `>=` | `{"gte": value}` | `date >= '2024-01-01'` |
| `<` | `{"lt": value}` | `revenue < 10000` |
| `<=` | `{"lte": value}` | `date <= '2024-12-31'` |
| `!=` | `{"ne": value}` | `status != 'cancelled'` |
| `IN (...)` | `[value1, value2]` | `region IN ('US', 'EU')` |

## Value types

- **Strings** — quoted: `region = 'US'`
- **Numbers** — no quotes: `revenue > 100000`
- **Booleans** — `true` or `false` (case-insensitive)
- **Dates** — quoted: `date >= '2024-01-01'`

## Limitations

**Not supported yet:** OR conditions, nested conditions, LIKE patterns, IS NULL / IS NOT NULL, complex expressions.

**Workaround:** Use `lookup_dimension_values` first to find valid values, then query with simple conditions.

## See also

- [Agent Tools](/concepts/tools) — All available tools
- [Semantic Models](/configuration/semantic-models) — Define dimensions and metrics
- [Query Examples](/concepts/how-it-works) — More query patterns

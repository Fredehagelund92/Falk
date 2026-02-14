# WHERE Clause Syntax

falk's MCP `query_metric` tool supports SQL-like WHERE clauses for filtering query results.

## Supported Syntax

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

Converts to:
- `{"date": {"gte": "2024-01-01"}}`
- `{"revenue": {"gt": 100000}}`
- `{"date": {"lte": "2024-12-31"}}`

### Multiple Conditions (AND)

```sql
region = 'US' AND date >= '2024-01-01'
region = 'US' AND date >= '2024-01-01' AND date <= '2024-12-31'
```

Converts to:
- `{"region": "US", "date": {"gte": "2024-01-01"}}`
- `{"region": "US", "date": {"gte": "2024-01-01", "lte": "2024-12-31"}}`

### IN Clause

```sql
region IN ('US', 'EU', 'APAC')
customer_segment IN ('Enterprise', 'SMB')
```

Converts to:
- `{"region": ["US", "EU", "APAC"]}`
- `{"customer_segment": ["Enterprise", "SMB"]}`

## Supported Operators

| Operator | BSL Format | Example |
|----------|------------|---------|
| `=` | Direct value | `region = 'US'` |
| `>` | `{"gt": value}` | `revenue > 1000` |
| `>=` | `{"gte": value}` | `date >= '2024-01-01'` |
| `<` | `{"lt": value}` | `revenue < 10000` |
| `<=` | `{"lte": value}` | `date <= '2024-12-31'` |
| `!=` | `{"ne": value}` | `status != 'cancelled'` |
| `IN (...)` | `[value1, value2]` | `region IN ('US', 'EU')` |

## Value Types

The parser automatically detects value types:

### Strings
Must be quoted with single or double quotes:
```sql
region = 'US'
region = "US"  -- also works
```

### Numbers
No quotes needed:
```sql
revenue > 100000
price <= 99.99
```

### Booleans
Use `true` or `false` (case-insensitive):
```sql
is_active = true
is_deleted = false
```

### Dates
Quoted strings (auto-detected):
```sql
date >= '2024-01-01'
created_at <= '2024-12-31'
```

## Combining Filters on Same Dimension

Multiple conditions on the same dimension are merged:

```sql
date >= '2024-01-01' AND date <= '2024-12-31'
```

Converts to:
```python
{"date": {"gte": "2024-01-01", "lte": "2024-12-31"}}
```

This creates a date range filter (between Jan 1 and Dec 31, 2024).

## Examples from MCP Clients

### Cursor

```
You: "Show me revenue for US customers in 2024"

→ Cursor calls:
query_metric(
    metric="revenue",
    dimensions=["customer_segment"],
    where="region = 'US' AND date >= '2024-01-01' AND date <= '2024-12-31'"
)
```

### Claude Desktop

```
You: "Compare Enterprise vs SMB revenue for Q1"

→ Claude calls:
query_metric(
    metric="revenue",
    dimensions=["customer_segment"],
    where="customer_segment IN ('Enterprise', 'SMB') AND date >= '2024-01-01' AND date <= '2024-03-31'"
)
```

## Limitations

### NOT Supported Yet

- **OR conditions** — Only AND is supported
- **Nested conditions** — No parentheses grouping
- **LIKE patterns** — No wildcards or pattern matching
- **IS NULL / IS NOT NULL** — No null checking
- **Complex expressions** — No calculated fields in WHERE

### Workarounds

For complex filters, use `lookup_dimension_values` first to find valid values, then query with simple conditions.

## How It Works

Under the hood, the WHERE parser:

1. Splits the string by `AND` keywords
2. Parses each condition for operator and value
3. Converts to BSL filter dict format
4. Merges multiple conditions on the same dimension

This makes MCP tool calls feel natural (SQL-like) while maintaining BSL's structured filter system for security and type safety.

## See Also

- [MCP Tools Reference](mcp-tools.md) — All available tools
- [Semantic Models](../configuration/semantic-models.md) — Define dimensions and metrics
- [Query Examples](../concepts/how-it-works.md) — More query patterns

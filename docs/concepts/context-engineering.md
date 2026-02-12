# Context Engineering

> falk uses a context-first approach to build intelligent data agents.

## Overview

Context engineering is the practice of organizing knowledge about your business, data, and domain so your AI agent can provide accurate, relevant answers.

**Key principle:** The right information, at the right time, in the right amount.

## Why Context Matters

Without proper context, your agent:
- Doesn't understand your business terminology
- Can't validate if results make sense
- Misses important data caveats
- Provides generic responses

With good context, your agent:
- Speaks your business language
- Validates results against benchmarks
- Proactively mentions data issues
- Provides tailored insights

## Project Structure

When you run `falk init`, you get a structure:

```
my-project/
├── RULES.md                          # Always included (keep concise!)
├── knowledge/                        # Business knowledge (loaded as needed)
│   ├── business.md                  # Business terms, company context
│   └── gotchas.md                   # Data quality issues, caveats
├── semantic_models.yaml             # Data layer (BSL)
└── falk_project.yaml               # Technical config
```

## RULES.md - Always Included

`RULES.md` is sent with **every single message** to your agent.

### What to Include

✅ **Agent behavior:**
- Tone of voice
- How to interact with users
- SQL code style
- Privacy/security rules

✅ **Orchestration instructions:**
```markdown
## Orchestration
For business context: Read `knowledge/business.md`
For data quality notes: Read `knowledge/gotchas.md`
```

✅ **Core business rules:**
- Data defaults (time ranges, limits)
- What to always exclude (test data)
- When to ask clarifying questions

### What NOT to Include

❌ Detailed metric definitions → Put in `knowledge/business.md`
❌ Long business glossaries → Put in `knowledge/business.md`
❌ SQL examples → Put in knowledge files
❌ Data quality issues → Put in `knowledge/gotchas.md`

**Why?** RULES.md is included in EVERY message. Keep it concise to:
- Reduce token costs
- Keep agent focused
- Improve performance

## Knowledge Directory - Loaded as Needed

The `knowledge/` directory contains detailed knowledge loaded only when relevant.

### Business Context

**`knowledge/business.md`**
- Business terms and definitions
- One canonical definition per term
- Include formulas and examples

```
**Customer**
- Definition: Completed at least one purchase
- SQL: WHERE order_count > 0
```

**`knowledge/business.md`** (company section)
- Company overview
- Products/services
- Customer journey
- Business model

### Domain Context

Each domain file contains specific knowledge:

**`knowledge/business.md`** (domain sections)
- CAC, conversion rate, attribution
- Campaign types and channels
- Marketing-specific SQL patterns

**`knowledge/business.md`**
- Revenue, MRR, ARR, churn
- Fiscal calendar
- Pricing and payment terms

**`knowledge/business.md`**
- DAU/MAU, feature adoption
- Retention cohorts
- Engagement metrics

### Data Quality Notes

**`knowledge/gotchas.md`**
- Known data issues
- Data freshness schedules
- Null handling
- Schema changes

**Why document issues?**
- Agent can proactively mention them
- Sets proper expectations
- Prevents incorrect conclusions

## Orchestration Pattern

The agent uses **orchestration** to load the right context at the right time.

### How It Works

1. User asks: "What's our CAC this month?"
2. Agent sees this in RULES.md:
   ```markdown
   For marketing questions: Read `knowledge/domains/marketing.md`
   ```
3. Agent reads marketing.md (contains CAC definition)
4. Agent composes accurate query

### Benefits

- **Token-efficient**: Only load what's needed
- **Focused**: Agent sees relevant context only
- **Scalable**: Add domains without bloating RULES.md

## Best Practices

### 1. MECE Principle (Mutually Exclusive, Collectively Exhaustive)

**Mutually Exclusive:**
- Each metric defined in ONE place only
- No conflicting definitions
- Clear ownership

**Collectively Exhaustive:**
- Cover all important domains
- Document all key metrics
- Address all major use cases

### 2. Keep It Modular

**Good:**
```
knowledge/
├── business.md  # Business terms, company context
└── gotchas.md   # Data quality issues
```

### 3. Use Examples

**Instead of:**
> "Customer: Someone who made a purchase"

**Write:**
```markdown
**Customer**
- Definition: Completed at least one purchase
- SQL: `WHERE order_count > 0`
- Example: User ID 12345 (placed order #9876)
- Excludes: Test orders, cancelled orders
```

### 4. Update Regularly

Context engineering is ongoing:
- New metrics? Add to domain files
- Data issue discovered? Document in gotchas.md
- Business term changed? Update glossary
- New product? Update business context

### 5. Validate with Real Questions

Test your context by asking real questions:
- "What's our CAC by channel?"
- "Show me churn rate trends"
- "Which features have highest adoption?"

Does the agent give correct, detailed answers? If not, improve context.

## Example: Adding a New Metric

Let's say you want to add "Customer Lifetime Value (LTV)" to your agent.

### 1. Add to Business Glossary

**`knowledge/business.md`:**
```
**LTV (Lifetime Value)**
- Predicted total revenue from a customer over their lifetime
- Formula: ARPU × (1 / churn_rate)
```

### 2. Add Detailed Definition in Domain File

**`knowledge/business.md`** (finance section):
```
### Customer Lifetime Value (LTV)

**Definition:**
Predicted total revenue from a customer over their lifetime.

**Calculation:**
```sql
WITH customer_metrics AS (
  SELECT 
    AVG(monthly_revenue) AS arpu,
    (COUNT(DISTINCT churned_customers) * 1.0 / 
     COUNT(DISTINCT total_customers)) AS monthly_churn_rate
  FROM customers
)
SELECT 
  arpu / NULLIF(monthly_churn_rate, 0) AS ltv
FROM customer_metrics;
```

**Benchmarks:**
- Our target LTV: $5,000
- Industry average: $4,200
- LTV:CAC ratio target: 3:1
```

### 3. Add to Semantic Models

Add the metric to `semantic_models.yaml`:

```yaml
models:
  - name: customer_metrics
    measures:
      - name: ltv
        expr: AVG(monthly_revenue) / NULLIF(churn_rate, 0)
        description: "Customer Lifetime Value"
```

### 4. Test

```bash
falk sync
falk query ltv
falk query ltv --group-by customer_segment
```


## Advanced: Multi-Team Setup

For larger organizations, use agent skills so each team can contribute domain expertise:

```yaml
# falk_project.yaml
skills:
  enabled: true
  directories:
    - "./skills"           # Shared skills
    - "./marketing/skills" # Marketing team skills
    - "./finance/skills"   # Finance team skills
```

**Benefits:**
- Teams own their domain skills
- Skills load progressively (only when relevant)
- Version control and PR reviews

## Resources

- [Boring Semantic Layer](https://github.com/pleonex/boring-semantic-layer) - Our semantic layer
- [Context Engineering Principles](#) - MECE and modular design

## Next Steps

1. **Run `falk init`** to create your context structure
2. **Customize `RULES.md`** — define how your agent should behave
3. **Fill context files** — add your business knowledge and domain context
4. **Test & iterate** — query your data and refine context based on results


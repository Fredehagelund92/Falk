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

## What Goes Where? (Quick Reference)

| File | Purpose | Loaded When | Keep It |
|------|---------|-------------|---------|
| `falk_project.yaml` | Technical config, LLM settings, quick context | Startup | Short, high-level |
| `RULES.md` | Agent behavior, tone, formatting rules | **Every message** | Concise, universal |
| `knowledge/business.md` | Business terms, glossary, company context | As needed | Business-specific |
| `knowledge/gotchas.md` | Data quality, known issues, caveats | As needed | Technical gotchas |
| `semantic_models.yaml` | Metrics, dimensions, data structure | Startup | Pure data layer |
| `.env` | API keys, secrets | Startup | Never commit |

**Key principle:** Short stuff in YAML/RULES.md, detailed knowledge in `knowledge/`.

---

## Project Structure

When you run `falk init`, you get a structure:

```
my-project/
├── falk_project.yaml                # Technical config (LLM, extensions)
├── RULES.md                          # Agent behavior (included with EVERY message)
├── knowledge/                        # Business knowledge (loaded as needed)
│   ├── business.md                  # Business terms, company context
│   └── gotchas.md                   # Data quality issues, caveats
├── semantic_models.yaml             # Data layer (metrics, dimensions)
└── .env                              # Secrets (not in git)
```

## File-by-File Guide

### 📄 `falk_project.yaml` — Quick Config

**Purpose:** High-level settings for quick edits

**Put here:**
- LLM provider and model (`provider: openai`, `model: gpt-4o`)
- 2-3 sentence business context ("We're a SaaS company...")
- 5-10 example questions
- 3-5 critical rules ("Revenue delayed 24h")
- Welcome message
- Extension toggles (langfuse, slack, charts)

**Don't put here:** Long business descriptions, detailed glossaries, data issues

---

### 📘 `RULES.md` — Agent Behavior (Always Included)

`RULES.md` is sent with **every single message** to your agent.

**Put here:**
- ✅ Tone of voice ("Be conversational, not robotic")
- ✅ Response structure ("Answer first, show data, add comparisons")
- ✅ Formatting rules ("Use nested bullets for hierarchical data")
- ✅ Interaction patterns ("When to ask clarifying questions")
- ✅ SQL code style ("Use CTEs, add LIMIT, explicit JOINs")
- ✅ Edge case handling ("How to respond to large results")

**Don't put here:**
- ❌ Detailed metric definitions → `knowledge/business.md`
- ❌ Long business glossaries → `knowledge/business.md`
- ❌ Data quality issues → `knowledge/gotchas.md`
- ❌ SQL examples → `knowledge/` files

**Why keep it short?** It's included in EVERY message. Bloating it:
- Increases token costs
- Dilutes focus
- Slows responses

---

### 📚 `knowledge/business.md` — Domain Knowledge

**Purpose:** What the business does and how it works

**Put here:**
- ✅ Company overview (what you sell, business model)
- ✅ Glossary with canonical definitions ("MRR = monthly recurring revenue")
- ✅ Customer journey (Awareness → Trial → Paid)
- ✅ Target segments (B2B enterprise, SMBs)
- ✅ Key metrics (North Star metric, why it matters)
- ✅ Seasonality patterns ("Q4 is 40% of revenue")

**Loaded:** Only when relevant to the current query

---

### 📚 `knowledge/gotchas.md` — Data Quality & Caveats

**Purpose:** Known issues, limitations, workarounds

**Put here:**
- ✅ Data freshness schedules ("Revenue synced daily at 6 AM")
- ✅ Known bugs ("Missing UTM params Aug 1-15, 2024")
- ✅ Table quirks ("`users.email` has 0.5% duplicates")
- ✅ Approximations ("15% blocked by ad blockers")
- ✅ Historical context ("New tracking started March 2024")

**Why document issues?** Agent proactively mentions them and sets proper expectations.

---

### 🗄️ `semantic_models.yaml` — Data Layer

**Purpose:** Metrics, dimensions, database structure

**Put here:**
- ✅ Metric formulas (`revenue = SUM(orders.amount)`)
- ✅ Dimension definitions (tables, columns, joins)
- ✅ Synonyms (`mrr` → `monthly_recurring_revenue`)
- ✅ Time grains (day, week, month, quarter)

**Don't put here:** Business context, behavior rules, quality notes

See [Semantic Models](../configuration/semantic-models.md) for details.

---

### 🔐 `.env` — Secrets

**Put here:**
- API keys (`OPENAI_API_KEY`, `LANGFUSE_SECRET_KEY`)
- Database credentials
- Slack tokens

**Never commit to git.** Use `.env.example` for documentation.

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
falk test --fast
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


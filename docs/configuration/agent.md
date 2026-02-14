# Project Configuration

`falk_project.yaml` is the technical configuration for your falk project (in project root). It controls agent behavior, extensions, and access control.

> **Note:** Business context and rules live in `RULES.md` and `knowledge/` files. See [Context Engineering](../concepts/context-engineering.md).

## Sections

### `agent` — LLM settings and behavior

```yaml
agent:
  provider: anthropic        # anthropic, openai, gemini
  model: claude-sonnet-4     # Model to use
  
  # Business context (brief summary)
  context: |
    We're a SaaS company selling analytics software.
    The funnel is: trials -> signups -> paid customers -> revenue.
  
  # Example questions (shown to users)
  examples:
    - "What's our revenue by region this month?"
    - "Show me top 5 customers by trials"
  
  # Rules the agent should follow
  rules:
    - "Revenue data has a 24-hour processing delay"
    - "Always mention the date range when showing results"
  
  # Welcome message for new conversations
  welcome: |
    Hi! I can help you explore your data.
    Try asking:
    - "What's our revenue by region?"
    - "Show me top customers"
```

### `extensions` — Integrations

```yaml
extensions:
  langfuse:
    enabled: true
    trace_all: true
    collect_feedback: true
  
  slack:
    enabled: true
    feedback_reactions: true
    channels: []  # Empty = all channels
  
  charts:
    enabled: true
    default_type: auto  # auto, bar, line, pie
    formats: [png, html]
  
  exports:
    enabled: true
    formats: [csv, excel, google_sheets]
    max_rows: 100000
```

### `access` — Data governance

```yaml
access:
  # access_policy: access_policy.yaml  # If set and file exists, row-level filtering enabled
```

### `skills` — Bring your own skills

```yaml
skills:
  enabled: false
  directories: ["./skills"]
```

See [Agent Skills](./skills.md) for details.

### `connection` — Database (inline)

```yaml
connection:
  type: duckdb
  database: data/warehouse.duckdb
```

BigQuery: `type: bigquery`, `project_id`, `dataset_id`. Snowflake: `type: snowflake`, `user`, `password`, `account`, `database`, `schema`.

### `paths` — File locations

```yaml
paths:
  semantic_models: semantic_models.yaml
```

### `advanced` — Technical settings

```yaml
advanced:
  auto_run: false
  max_tokens: 4096
  temperature: 0.1
  max_rows_per_query: 10000
  query_timeout_seconds: 30
  max_retries: 3
  log_level: INFO
```

## Full Example

```yaml
version: 1

connection:
  type: duckdb
  database: data/warehouse.duckdb

agent:
  provider: anthropic
  model: claude-sonnet-4
  context: |
    We're a SaaS analytics company.
  rules:
    - "Revenue data has a 48-hour delay"
  examples:
    - "What's our revenue by region?"

extensions:
  langfuse:
    enabled: true
  charts:
    enabled: true
  exports:
    enabled: true

access:
  # access_policy: access_policy.yaml  # optional

paths:
  semantic_models: semantic_models.yaml

advanced:
  auto_run: false
  max_tokens: 4096
  temperature: 0.1
  max_rows_per_query: 10000
  query_timeout_seconds: 30
```

## What Goes Where?

falk uses multiple config files for different purposes. Here's how to decide where content should live:

### 📄 `falk_project.yaml` — Quick Config & Examples

**Purpose:** High-level settings an analyst can quickly edit

**Put here:**
- ✅ LLM settings (`provider: openai`, `model: gpt-4o`)
- ✅ Quick business context (2-3 sentences: "We're a SaaS company...")
- ✅ Example questions (5-10 sample queries users can try)
- ✅ Top-level rules (3-5 critical constraints: "Revenue delayed 24h")
- ✅ Welcome message
- ✅ Extension toggles (langfuse, slack, charts on/off)

**Keep it:** Short, high-signal, quick-scan. Think "settings file."

---

### 📘 `RULES.md` — Agent Behavior & Style

**Purpose:** How the agent acts, responds, and formats answers

**Put here:**
- ✅ Tone & personality ("Be conversational, not robotic")
- ✅ Response structure ("Answer first, show data, add comparisons")
- ✅ Formatting rules ("Use bullets, no tables, nested lists for hierarchical data")
- ✅ Interaction patterns ("When to ask clarifying questions")
- ✅ SQL style guide ("Use CTEs, add LIMIT, explicit JOINs")
- ✅ Edge cases ("How to handle exports, large results, errors")

**Keep it:** Process-oriented, universal rules that apply to any query.

**Location:** `RULES.md` in project root (included with every agent message)

---

### 📚 `knowledge/business.md` — Domain Knowledge

**Purpose:** What the business does and how it works

**Put here:**
- ✅ Company overview (What you sell, business model)
- ✅ Glossary ("MRR = monthly recurring revenue")
- ✅ Customer journey (Awareness → Trial → Paid → Active)
- ✅ Target segments (B2B enterprise, SMBs, etc.)
- ✅ Key metrics (North Star metric, why each metric matters)
- ✅ Seasonality ("Q4 is 40% of revenue due to holidays")

**Keep it:** Business-specific, changes when your business evolves.

**Location:** `knowledge/business.md` (loaded dynamically as needed)

---

### 📚 `knowledge/gotchas.md` — Data Quality & Caveats

**Purpose:** Known issues, limitations, and workarounds

**Put here:**
- ✅ Data freshness ("Revenue synced daily at 6 AM UTC")
- ✅ Known bugs ("Missing UTM params Aug 1-15, 2024")
- ✅ Table quirks ("`users.email` has 0.5% duplicates")
- ✅ Approximations ("15% of web events blocked by ad blockers")
- ✅ Historical context ("New tracking started March 2024")

**Keep it:** Technical gotchas the agent should proactively mention.

**Location:** `knowledge/gotchas.md` (loaded when relevant to queries)

---

### 🗄️ `semantic_models.yaml` — Data Definitions

**Purpose:** Metrics, dimensions, and database structure

**Put here:**
- ✅ Metric formulas (`revenue = SUM(orders.amount)`)
- ✅ Dimension definitions (tables, columns, relationships)
- ✅ Synonyms (`mrr` → `monthly_recurring_revenue`)
- ✅ Time grains (day, week, month, quarter)

**Keep it:** Pure data layer. No business logic or behavior.

See [Semantic Models](./semantic-models.md) for full documentation.

---

### 🔐 `.env` — Secrets

**Purpose:** API keys and credentials

**Put here:**
- ✅ `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
- ✅ `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`
- ✅ `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`
- ✅ Database credentials (if not using local DuckDB)

**Never commit to git.** Use `.env.example` for documentation.

---

## Quick Decision Tree

| Content | Where It Goes |
|---------|---------------|
| "What LLM to use" | `falk_project.yaml` → `agent.provider`, `agent.model` |
| "Revenue = orders.amount WHERE status='paid'" | `semantic_models.yaml` → metric definition |
| "Always use nested bullets" | `RULES.md` → Response Formatting |
| "MRR = monthly recurring revenue" | `knowledge/business.md` → Glossary |
| "Revenue delayed 24h" | `knowledge/gotchas.md` → Data Freshness |
| "Be conversational" | `RULES.md` → Tone of Voice |
| Sample questions | `falk_project.yaml` → `agent.examples` |
| Customer journey stages | `knowledge/business.md` → Customer Journey |
| SQL style preferences | `RULES.md` → SQL Code Style |
| "`users.email` has duplicates" | `knowledge/gotchas.md` → Table-Specific Notes |

---

## File Relationship Summary

| File | Loaded When | Purpose |
|------|-------------|---------|
| `falk_project.yaml` | Startup | Technical config, quick context |
| `semantic_models.yaml` | Startup | Data structure (BSL) |
| `RULES.md` | Every message | Agent behavior & style |
| `knowledge/*.md` | As needed | Deep domain knowledge |
| `.env` | Startup | Secrets (not in git) |

# Knowledge & Feedback

The agent learns from config files and context. It improves over time through a feedback loop.

## What the agent knows

### 1. Vocabulary — `semantic_models.yaml`

```yaml
measures:
  revenue:
    expr: _.revenue.sum()
    synonyms: ["sales", "income", "turnover"]
dimensions:
  region:
    expr: _.region
    synonyms: ["territory", "area"]
```

### 2. Gotchas — `semantic_models.yaml`

```yaml
measures:
  revenue:
    gotchas: "Revenue has a 48-hour reporting delay"
```

The agent proactively mentions these when relevant.

### 3. Behavior — `RULES.md`

Tone, SQL style, privacy rules, orchestration:

```markdown
## Orchestration
For business context: Read `knowledge/business.md`
For data quality notes: Read `knowledge/gotchas.md`
```

### 4. Domain knowledge — `knowledge/`

Detailed knowledge loaded on demand:

- `knowledge/business.md` — business terms, company context
- `knowledge/gotchas.md` — known data issues

See [Context Engineering](./context-engineering.md).

## Feedback loop

```
User asks question
     ↓
Agent answers → trace in LangFuse
     ↓
User reacts 👍 or 👎 → score in LangFuse
     ↓
Data steward reviews low scores
     ↓
Updates config/context files → agent improves
```

## The improvement cycle

1. **Find issues** — filter LangFuse traces by low scores
2. **Understand why** — see the full trace (query → tools → response)
3. **Fix the source** — update synonyms, gotchas, rules, or context
4. **Write a test** — add a case to `evals/` to prevent regression
5. **Verify** — `falk evals evals/`

## Everything is files

All agent knowledge lives in version-controlled files:

| File | Purpose |
|------|---------|
| `semantic_models.yaml` | Data definitions + synonyms + gotchas |
| `falk_project.yaml` | Technical configuration |
| `RULES.md` | Agent behavior |
| `knowledge/` | Domain knowledge |

No database. No migrations. PR-reviewed and version-controlled.

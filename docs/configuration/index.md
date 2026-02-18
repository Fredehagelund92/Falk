# Configuration

falk uses **files, not databases**. All configuration is version-controlled and PR-reviewable.

| File | Purpose | Loaded When | Who Edits |
|------|---------|-------------|-----------|
| `falk_project.yaml` | LLM settings, session config, quick context | Startup | Platform team |
| `semantic_models.yaml` | Metrics, dimensions, data structure | Startup | Data engineers |
| `RULES.md` | Agent behavior, tone, formatting | **Every message** | Anyone |
| `knowledge/business.md` | Business terms, glossary, company context | Startup (if enabled) | Domain experts |
| `knowledge/gotchas.md` | Data quality issues, caveats | Startup (if enabled) | Data stewards |
| `.env` | API keys, secrets | Startup | DevOps |

## What Goes Where?

**"What LLM should we use?"** → `falk_project.yaml`  
**"Revenue = SUM(orders.amount)"** → `semantic_models.yaml`  
**"Always use nested bullets"** → `RULES.md`  
**"MRR = monthly recurring revenue"** → `knowledge/business.md`  
**"Revenue delayed 24h"** → `knowledge/gotchas.md`  
**"Be conversational, not robotic"** → `RULES.md`  
**Example questions** → `falk_project.yaml`  

See [Context Engineering](../concepts/context-engineering.md) for detailed guidance.

---

## How It Fits Together

```
semantic_models.yaml    →  "What data exists" (metrics, dimensions)
falk_project.yaml       →  "How the agent runs" (LLM, session store)
RULES.md                →  "How the agent behaves" (always included)
knowledge/              →  "Deep domain knowledge" (startup when enabled)
```

Update any config file and the agent picks up the changes automatically — no prompt editing needed.

## Reference

- [Semantic Models](semantic-models.md) — metrics, dimensions, synonyms, gotchas
- [Project Config](agent.md) — LLM provider, session store, runtime settings
- [Metric Relationships](metric-relationships.md) — define how metrics relate
- [LLM Providers](llm-providers.md) — OpenAI, Anthropic, Gemini setup

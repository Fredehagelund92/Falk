# Configuration

falk uses **files, not databases**. All configuration is version-controlled and PR-reviewable.

## Config files

| File | Purpose | Loaded when | Who edits |
|------|---------|-------------|-----------|
| `falk_project.yaml` | LLM settings, session config, quick context | Startup | Platform team |
| `semantic_models.yaml` | Metrics, dimensions, data structure | Startup | Data engineers |
| `RULES.md` | Agent behavior, tone, formatting | Startup (included in system prompt) | Anyone |
| `knowledge/business.md` | Business terms, glossary, company context | Startup (if enabled) | Domain experts |
| `knowledge/gotchas.md` | Data quality issues, caveats | Startup (if enabled) | Data stewards |
| `.env` | API keys, secrets | Startup | DevOps |

## What goes where

| Question | File |
|----------|------|
| "What LLM should we use?" | `falk_project.yaml` |
| "Revenue = SUM(orders.amount)" | `semantic_models.yaml` |
| "Always use nested bullets" | `RULES.md` |
| "MRR = monthly recurring revenue" | `knowledge/business.md` |
| "Revenue delayed 24h" | `knowledge/gotchas.md` |
| "Be conversational, not robotic" | `RULES.md` |
| Example questions | `falk_project.yaml` |
| Custom project tools | `falk_project.yaml` + Python modules |

See [Context Engineering](/concepts/context-engineering) for detailed guidance.

## How it fits together

```
semantic_models.yaml  →  "What data exists" (metrics, dimensions)
falk_project.yaml     →  "How the agent runs" (LLM, session store)
RULES.md             →  "How the agent behaves" (always included)
knowledge/           →  "Deep domain knowledge" (startup when enabled)
```

Update any config file and the agent picks up the changes automatically — no prompt editing needed.

## Reference

- [Semantic Models](/configuration/semantic-models) — metrics, dimensions, synonyms, gotchas
- [Project Config](/configuration/agent) — LLM provider, session store, extensions, runtime settings
- [Memory](/concepts/memory) — what persists (session store, knowledge, feedback)
- [Agent Tools](/concepts/tools) — built-in tools and custom extensions
- [Metric Relationships](/configuration/metric-relationships) — define how metrics relate
- [LLM Providers](/configuration/llm-providers) — OpenAI, Anthropic, Gemini setup

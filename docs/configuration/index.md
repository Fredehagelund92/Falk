# Configuration

falk uses **files, not databases**. All configuration is version-controlled and PR-reviewable.

| File | Purpose | Who edits |
|------|---------|-----------|
| `semantic_models.yaml` | Metrics, dimensions, synonyms, gotchas | Data engineers |
| `falk_project.yaml` | LLM provider, extensions, access control | Platform team |
| `RULES.md` | Agent behavior (tone, orchestration, rules) | Anyone |
| `knowledge/` | Business terms, data quality gotchas | Domain experts |
| `.env` | API keys and secrets | DevOps |

## How it fits together

```
semantic_models.yaml    →  "What data exists"
falk_project.yaml       →  "How the agent runs"
RULES.md + knowledge/   →  "How the agent behaves"
```

Update any config file and the agent picks up the changes automatically — no prompt editing needed.

## Reference

- [Semantic Models](semantic-models.md) — metrics, dimensions, synonyms, gotchas
- [Project Config](agent.md) — LLM provider, extensions, access control
- [Metric Relationships](metric-relationships.md) — define how metrics relate
- [Agent Skills](skills.md) — bring your own skills (pydantic-ai-skills)
- [LLM Providers](llm-providers.md) — OpenAI, Anthropic, Gemini setup

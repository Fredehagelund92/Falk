# Learning & Feedback

The agent does not learn from conversations. It improves when humans update config files based on feedback and evals.

## Feedback loop

```
User asks question
     ↓
Agent answers → trace in Logfire
     ↓
User reacts 👍 or 👎 → score in Logfire
     ↓
Data steward reviews low scores
     ↓
Updates config/context files → agent improves
```

## The improvement cycle

1. **Find issues** — filter Logfire traces by low scores
2. **Understand why** — see the full trace (query → tools → response)
3. **Fix the source** — update synonyms, gotchas, rules, or context
4. **Write a test** — add a case to `evals/` to prevent regression
5. **Verify** — `falk test`

## Everything is files

All agent knowledge lives in version-controlled files. No database. No migrations. PR-reviewed and version-controlled.

## See also

- [Context](/concepts/context) — where vocabulary, gotchas, and domain knowledge live
- [Memory](/concepts/memory) — what persists (knowledge vs session vs feedback)

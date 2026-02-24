# Context Engineering

falk uses layered context so teams can customize behavior without editing core code.

## Core principle

Put each type of information in one canonical place:

| Source | Purpose |
|--------|---------|
| `falk_project.yaml` | Runtime config |
| `RULES.md` | Behavior policy |
| `knowledge/business.md` | Domain/company knowledge |
| `knowledge/gotchas.md` | Data caveats |
| `semantic_models.yaml` | Metric/dimension definitions |

This keeps prompts deterministic and easier to maintain.

## Load model

| Source | Loaded |
|--------|--------|
| `falk_project.yaml` | Startup |
| `semantic_models.yaml` | Startup |
| `RULES.md` | Startup (included in prompt) |
| `knowledge/business.md` | Startup when `agent.knowledge.enabled: true` |
| `knowledge/gotchas.md` | Startup when `agent.knowledge.enabled: true` |

## Prompt precedence

When instructions conflict, precedence is:

1. Built-in system prompt defaults
2. `RULES.md`
3. Inline project config (`agent.rules`, `agent.custom_sections`)
4. Knowledge files (`knowledge/*.md`)
5. Semantic metadata (synonyms, descriptions, gotchas)

## What goes where

### `falk_project.yaml`

Use for: quick business summary, sample questions, short project rules, global caveats, knowledge loading controls.

### `RULES.md`

Use for: response/process standards, formatting expectations, escalation and error style. Keep it concise and universal.

### `knowledge/business.md`

Use for: glossary and domain definitions, business model and customer journey, interpretation context.

### `knowledge/gotchas.md`

Use for: data freshness notes, known quality gaps, caveats users should hear when relevant.

### `semantic_models.yaml`

Use for: metric formulas, dimensions and joins, semantic synonyms, model metadata.

## See also

- [Memory](/concepts/memory) — how knowledge files fit into the persistence model
- [Tuning the agent](/configuration/tuning) — improving answer quality (context, evals, model choice)

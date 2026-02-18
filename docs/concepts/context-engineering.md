# Context Engineering

falk uses layered context so teams can customize behavior without editing core code.

## Core Principle

Put each type of information in one canonical place:

- **Runtime config:** `falk_project.yaml`
- **Behavior policy:** `RULES.md`
- **Domain/company knowledge:** `knowledge/business.md`
- **Data caveats:** `knowledge/gotchas.md`
- **Metric/dimension definitions:** `semantic_models.yaml`

This keeps prompts deterministic and easier to maintain across many companies.

## Load Model (Phase 1)

| Source | Loaded |
|---|---|
| `falk_project.yaml` | Startup |
| `semantic_models.yaml` | Startup |
| `RULES.md` | Startup (included in prompt) |
| `knowledge/business.md` | Startup when `agent.knowledge.enabled: true` |
| `knowledge/gotchas.md` | Startup when `agent.knowledge.enabled: true` |

`agent.knowledge.load_mode: on_demand` is reserved for future work.

## Prompt Precedence

When instructions conflict, precedence is:

1. Built-in system prompt defaults
2. `RULES.md`
3. Inline project config (`agent.rules`, `agent.custom_sections`)
4. Knowledge files (`knowledge/*.md`)
5. Semantic metadata (synonyms, descriptions, gotchas)

## What Goes Where

### `falk_project.yaml`
Use for:
- quick business summary (`agent.context`)
- sample questions (`agent.examples`)
- short project rules (`agent.rules`)
- global caveats (`agent.gotchas`)
- knowledge loading controls (`agent.knowledge`)

### `RULES.md`
Use for:
- response/process standards that apply broadly
- formatting expectations
- escalation and error style

Keep it concise and universal.

### `knowledge/business.md`
Use for:
- glossary and domain definitions
- business model and customer journey
- interpretation context

### `knowledge/gotchas.md`
Use for:
- data freshness notes
- known quality gaps
- caveats users should hear when relevant

### `semantic_models.yaml`
Use for:
- metric formulas
- dimensions and joins
- semantic synonyms
- model metadata

## Why This Matters

This separation improves:
- consistency across companies/projects
- maintenance and onboarding
- prompt clarity and lower drift
- reliable customization without code edits

## Phase 2 Note

Access policy / row-level governance is intentionally deferred to phase 2.

## See also

- [Tuning the agent](../configuration/tuning.md) — improving answer quality (context, evals, model choice).

# Tuning the Agent

Improving answer quality is usually more about **context, policy, and evaluation** than swapping to a larger model.

## What to do first (highest impact)

### 1. Improve context and knowledge

- **Fill in real gotchas.** Replace scaffold placeholders in `knowledge/gotchas.md` with concrete caveats (freshness, delays, segment definitions, historical gaps). The agent uses these to warn users and avoid wrong interpretations.
- **Add domain and glossary.** Use `knowledge/business.md` for glossary terms, business model, and how metrics are interpreted in your company.
- **Use semantic metadata.** In `semantic_models.yaml`, add `synonyms` and `description` (and metric/dimension gotchas) so the agent maps natural language to the right metrics and dimensions.

Better grounding in your config and knowledge files often improves correctness more than upgrading the model.

### 2. Adjust scope and policy

The built-in system prompt is **data-only**: it tells the agent to answer from knowledge in the prompt or from tools, and to respond "This request is outside my capabilities" for anything else.

If you want the bot to be more generally helpful, relax or change that policy via `RULES.md`. If you stay data-only, keep the default; it reduces drift and off-topic answers.

### 3. Add a small eval harness

- Add 30–50 real questions under `evals/` (ambiguous phrasing, entity resolution, date ranges, cases where gotchas apply).
- Track: correct metric/dimension choice, correct filters, and whether answers mention caveats when relevant.
- Use this to compare prompt changes and model choices instead of ad-hoc testing.

### 4. Model and routing

- **Better model:** Upgrading the model can help, but gains are often incremental compared to fixing context and evals.
- **Routing:** Use a fast/cheap default model and escalate to a stronger model only when confidence is low or the question is complex.

### 5. Timeouts ("query took too long")

- `advanced.model_timeout_seconds` — how long the LLM has to respond (single turn)
- `advanced.query_timeout_seconds` — timeout for each tool call (warehouse query)
- `advanced.slack_run_timeout_seconds` — outer timeout for a whole Slack run

If you see "query took too long," check which layer is slow and raise the appropriate timeout.

### 6. Tool loops

If the agent seems to get stuck repeatedly calling tools instead of answering, lower `advanced.tool_calls_limit` and/or `advanced.request_limit`.

## Order of operations

1. Fix **policy and context** (gotchas, business knowledge, synonyms).
2. Add **evals** and iterate on prompts and knowledge using them.
3. Then tune **model choice** (and routing if you add it).

## See also

- [Context](/concepts/context) — where to put context
- [Project Config](/configuration/agent) — `falk_project.yaml` and related files
- [Evals](/concepts/evals) — how to define and run evaluation cases

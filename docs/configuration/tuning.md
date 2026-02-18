# Tuning the Agent

Improving answer quality is usually more about **context, policy, and evaluation** than swapping to a larger model. This page summarizes high-leverage tuning options.

## What to do first (highest impact)

### 1. Improve context and knowledge

- **Fill in real gotchas.** The scaffold `knowledge/gotchas.md` is mostly placeholders. Replace them with concrete caveats (freshness, delays, segment definitions, historical gaps). The agent uses these to warn users and avoid wrong interpretations.
- **Add domain and glossary.** Use `knowledge/business.md` for glossary terms, business model, and how metrics are interpreted in your company. This reduces ambiguity and wrong metric choice.
- **Use semantic metadata.** In `semantic_models.yaml`, add `synonyms` and `description` (and metric/dimension gotchas) so the agent maps natural language to the right metrics and dimensions.

Better grounding in your config and knowledge files often improves correctness more than upgrading the model.

### 2. Adjust scope and policy (if you want broader answers)

The built-in system prompt is intentionally **data-only**: it tells the agent to answer from knowledge in the prompt or from tools, and to respond *"This request is outside my capabilities"* for anything else (e.g. code, emails, general advice).

- If you want the bot to be more generally helpful, you’ll need to relax or change that policy (e.g. via `RULES.md` or future prompt extension points). Today the strict scope is by design to keep behavior predictable for data workloads.
- If you stay data-only, keep the default; it reduces drift and off-topic answers.

### 3. Add a small eval harness

- Add 30–50 real questions (ambiguous phrasing, entity resolution, date ranges, cases where gotchas apply) under `evals/`.
- Track: correct metric/dimension choice, correct filters, and whether answers are useful and mention caveats when relevant.
- Use this to compare prompt changes and model choices instead of relying on ad-hoc testing.

### 4. Model and routing

- **Better model:** Upgrading the model (e.g. to a larger or newer one) can help, but gains are often incremental compared to fixing context and evals.
- **Routing:** Use a fast/cheap default model and escalate to a stronger model only when confidence is low, tools fail, or the question is complex. This improves both quality and cost.

### 5. Timeouts ("query took too long")

- **Model vs query vs Slack:** `advanced.model_timeout_seconds` limits how long the LLM has to respond (single turn). `advanced.query_timeout_seconds` limits each tool call (e.g. warehouse query). `advanced.slack_run_timeout_seconds` is the outer timeout for a whole Slack run (model + tools). If you see "query took too long," check which layer is slow: raise `model_timeout_seconds` for slow/reasoning models, `query_timeout_seconds` for heavy or slow warehouse queries, or `slack_run_timeout_seconds` if the whole Slack request needs more time.

### 6. Tool loops

- If the agent seems to \"get stuck\" repeatedly calling tools instead of answering, lower `advanced.tool_calls_limit` and/or `advanced.request_limit`. The system prompt also instructs the model to answer once it has data from `query_metric` instead of re-querying.\n*** End Patch```}"/>

## Order of operations

A practical order:

1. Fix **policy and context** (gotchas, business knowledge, synonyms).
2. Add **evals** and iterate on prompts and knowledge using them.
3. Then tune **model choice** (and routing if you add it).

## Related docs

- [Context engineering](../concepts/context-engineering.md) — where to put context (RULES, knowledge, semantic_models).
- [Agent configuration](agent.md) — `falk_project.yaml` and related files.
- [Evals](../concepts/evals.md) — how to define and run evaluation cases.

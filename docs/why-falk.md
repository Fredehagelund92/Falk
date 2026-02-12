# Why falk?

falk exists to answer a simple question:

> **How can we let AI query our warehouse _safely_ without breaking governance and trust?**

Most new agents start from "let the model write SQL over your whole warehouse". That’s powerful, but it ignores how data teams actually work: governed metrics, curated models, and hard‑won trust in a handful of numbers (revenue, CAC, churn, etc.). falk is built to respect that reality.

## Why we built falk

### Metrics need a home, not a prompt

In real companies, "what is revenue?" is not a prompt — it’s a contract:

- Finance has a specific definition (filters, joins, time windows)
- BI dashboards use that same definition
- Teams get very upset if a new tool shows different numbers

falk makes the **semantic model** the source of truth:

- Metrics and dimensions live in versioned YAML (semantic models)
- The agent reads those models instead of guessing from tables
- Every interface (Slack, CLI, web, skills) uses the same definitions

### Governance can’t be an afterthought

Letting an LLM query arbitrary tables is fine for exploration, but not for production analytics. We built falk so that:

- Only **approved metrics/dimensions** are exposed
- Access control can be enforced at the semantic layer
- You can reason about **what the agent is allowed to know**

Instead of "LLM + warehouse", falk is **LLM + semantic layer + warehouse**.

### "Why" questions should be first‑class

Most tools stop at "what":

- "Revenue last month"  
- "Top 10 customers"  

But real conversations quickly become "why":

- "Why did revenue go up?"  
- "Which segment drove the change?"  
- "Was it volume or price?"  

Because falk understands metrics and dimensions from the semantic layer, it can:

- Decompose metric changes across dimensions (regions, products, segments)
- Use **related_metrics** (e.g. revenue = orders × AOV) to explain drivers
- Answer "why" with structure, not just more numbers

### Agents should be tools, not monoliths

We wanted something that works well in many contexts:

- CLI for skills, CI, automation (`falk query`, `falk decompose`, `falk sync`)
- Pydantic‑AI agent for conversational interfaces (Slack, web)
- Clear JSON outputs so other agents/orchestrators can treat falk as a **governed data tool**

The design goal: **falk is the data brain you plug other agents into**, not another all‑in‑one assistant.

## What falk gives you

- **Governed access** — only metrics/dimensions you’ve modeled
- **Consistent numbers** — same as your BI/semantic layer
- **Context‑aware answers** — uses descriptions, synonyms, gotchas
- **Why‑first analytics** — metric decomposition and related metrics
- **Tool‑first design** — CLI and agent tools meant to be composed

## When falk makes sense

falk is built for teams that:

- Already have (or want) a semantic layer
- Care that "revenue" means the same thing everywhere
- Need AI to **respect governance**, not bypass it
- Want agents/skills that can safely answer data questions

If you just want to let a model explore every table freely, falk is probably not the right choice. If you want **governed AI access to trusted metrics**, that’s exactly what falk is for.

---

**Next:** [Quick Start](getting-started/quickstart.md) — see what it feels like to define a metric once and query it everywhere.


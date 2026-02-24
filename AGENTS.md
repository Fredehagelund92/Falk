# AGENTS

Repository guidance for coding agents working on `falk`.

## Project Snapshot

- `falk` is a governed data agent powered by semantic-layer metrics.
- Core package lives in `src/falk/`; interface wrappers live in `app/`.
- Important domains:
  - `src/falk/llm/` for agent/tool behavior
  - `src/falk/backends/` for observability/session/memory backends
  - `app/mcp.py`, `app/web.py`, `app/slack.py` for runtime entrypoints
  - `docs/` for documentation (Docusaurus in repo root)

## Local Dev Commands

- Setup: `uv venv && uv sync --extra dev`
- Run tests: `pytest`
- Lint: `ruff check .`
- Run web UI: `falk chat`
- Run MCP server: `falk mcp`
- Run Slack bot: `falk slack`
- Build docs: `npm run build` (or `npm run start` for dev server)

## Change Guidelines

- Keep `src/falk/` library-first; treat `app/` as thin wrappers.
- Preserve semantic-layer constraints: never introduce logic that invents data.
- Prefer small, focused changes with clear rationale in commits/PRs.
- Update docs when behavior, config, or CLI usage changes.
- Keep scaffold templates in `src/falk/scaffold/` aligned with runtime expectations.

## Validation Checklist Before Shipping

- Tests or targeted checks pass for touched behavior.
- `ruff check .` passes for edited files.
- User-facing docs/examples are updated when needed.
- New config/env options are reflected in `env.example` and docs.

## Safety Notes

- Never commit secrets (`.env`, keys, tokens, credentials).
- Avoid destructive git operations unless explicitly requested.
- Do not silently change public behavior without documenting it.

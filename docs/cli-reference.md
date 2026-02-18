# CLI Reference

Run `falk --help` or `falk <command> --help` for the latest options.

---

## `falk init`

Scaffold a new falk project.

```bash
falk init my-project
falk init .                    # scaffold into current directory
falk init analytics --warehouse snowflake --no-sample-data
```

Creates: `RULES.md`, `knowledge/`, `semantic_models.yaml`, `falk_project.yaml`, `.env.example`, and sample data (DuckDB). Use `falk init .` to add scaffold files to the current directory instead of creating a subdirectory.

---

## `falk config`

Show current configuration.

```bash
falk config
falk config --json
```

---

## `falk test`

Validate project configuration, semantic models, and run test cases.

```bash
falk test                    # Full test suite
falk test --fast             # Quick validation only
falk test --no-connection    # Skip connection test
falk test --evals-only       # Only run evals
falk test --verbose          # Detailed output
```

**Validation phases:**
1. Configuration validation (falk_project.yaml)
2. Semantic layer validation (BSL models)
3. Warehouse connection test (optional)
4. Agent initialization test (optional)
5. Evaluation test cases (if evals/ exists)

---

## `falk mcp`

Start the MCP server.

```bash
falk mcp
```

Exposes tools via Model Context Protocol for use with:
- Cursor
- Claude Desktop
- Any MCP-compatible client

See [MCP Guide](getting-started/mcp.md) for setup instructions.

---

## `falk chat`

Start the web UI server.

```bash
falk chat                    # default: port 8000
falk chat --port 3000        # custom port
falk chat --no-reload        # disable auto-reload
```

---

## `falk slack`

Start the Slack bot.

```bash
falk slack
```

Requires `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` in `.env`.

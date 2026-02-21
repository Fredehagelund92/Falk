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
falk config --all
```

---

## `falk validate`

Validate project configuration, semantic models, and optional runtime checks.

```bash
falk validate                 # Full validation (including connection + agent init)
falk validate --fast          # Config/semantic/knowledge checks only
falk validate --no-connection # Skip warehouse connection test
falk validate --no-agent      # Skip agent initialization test
falk validate --verbose       # Show details for each check
```

**Validation phases include:**
1. Configuration validation (falk_project.yaml)
2. Semantic layer validation (BSL models)
3. Knowledge file validation
4. Warehouse connection test (optional)
5. Agent initialization test (optional)

---

## `falk test`

Run eval cases from `evals/` to verify behavior.

```bash
falk test                      # Run all eval files (*.yaml)
falk test --pattern "*.yaml"   # Choose eval file glob
falk test --tags access,gotchas
falk test --verbose
```

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

Start local web chat with the data agent (Pydantic AI built-in web UI).

```bash
falk chat
```

**Behavior:**
- Starts the local web server at `http://127.0.0.1:8000`.
- Uses Pydantic AI's built-in web UI (no separate frontend required).

---

## `falk access-test`

Run a question as a specific user identity to test access policies.

```bash
falk access-test --list-users
falk access-test --user analyst@company.com
falk access-test --user viewer@company.com --question "Describe the orders metric"
```

---

## `falk slack`

Start the Slack bot.

```bash
falk slack
```

Requires `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` in `.env`.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `falk chat` — DataAgent init fails | Run `falk validate` to check configuration. Ensure `.env` has required API keys (e.g. `OPENAI_API_KEY`). |
| Warehouse connection error | Check `falk_project.yaml` and `profiles.yml` for correct database connection. |

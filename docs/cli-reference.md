# CLI Reference

Run `falk --help` or `falk <command> --help` for the latest options.

## `falk init`

Scaffold a new falk project.

```bash
falk init my-project
falk init .                    # scaffold into current directory
falk init analytics --warehouse snowflake --no-sample-data
```

Creates: `RULES.md`, `knowledge/`, `semantic_models.yaml`, `falk_project.yaml`, `.env.example`, and sample data (DuckDB).

## `falk config`

Show current configuration.

```bash
falk config
falk config --all
```

## `falk validate`

Validate project configuration, semantic models, and optional runtime checks.

```bash
falk validate                 # Full validation (including connection + agent init)
falk validate --fast          # Config/semantic/knowledge checks only
falk validate --no-connection # Skip warehouse connection test
falk validate --no-agent      # Skip agent initialization test
falk validate --verbose       # Show details for each check
```

**Validation phases:** Configuration, semantic layer, knowledge files, warehouse connection (optional), agent initialization (optional).

## `falk test`

Run eval cases from `evals/` to verify behavior.

```bash
falk test
falk test --pattern "*.yaml"
falk test --tags access,gotchas
falk test --verbose
```

## `falk mcp`

Start the MCP server.

```bash
falk mcp
```

Exposes tools via Model Context Protocol for use with Cursor, Claude Desktop, or any MCP-compatible client. See [MCP Guide](/getting-started/mcp) for setup instructions.

## `falk chat`

Start local web chat with the data agent.

```bash
falk chat
```

Starts the web server at `http://127.0.0.1:8000`. Uses Pydantic AI's built-in web UI.

## `falk access-test`

Run a question as a specific user identity to test access policies.

```bash
falk access-test --list-users
falk access-test --user analyst@company.com
falk access-test --user viewer@company.com --question "Describe the orders metric"
```

## `falk slack`

Start the Slack bot.

```bash
falk slack
```

Requires `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` in `.env`.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `falk chat` — DataAgent init fails | Run `falk validate`. Ensure `.env` has required API keys (e.g. `OPENAI_API_KEY`). |
| Warehouse connection error | Check `falk_project.yaml` and `profiles.yml` for correct database connection. |

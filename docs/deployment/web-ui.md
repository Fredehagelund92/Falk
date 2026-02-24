# Web UI

Local web chat for testing, powered by Pydantic AI's built-in web interface.

## Run

```bash
falk chat
```

Opens at `http://127.0.0.1:8000`. No separate frontend is required.

## When to use

- **Local development** — test queries before deploying to Slack
- **Debugging** — validate prompt/tool behavior in a browser
- **Demos** — show the agent to stakeholders quickly

## Backend API (optional)

Start the web app directly if needed:

```bash
uv run uvicorn app.web:app --reload
```

The `falk chat` command uses this same app. All logic lives in the `falk` library — the same code powers the CLI chat, Slack bot, and MCP server.

# Web UI

A local ChatGPT-like interface for testing — powered by Pydantic AI's built-in web server.

## Run

```bash
falk chat
```

Opens at [http://localhost:8000](http://localhost:8000).

Options:

```bash
falk chat --port 3000        # Custom port
falk chat --no-reload        # Disable auto-reload
```

## When to use

- **Local development** — test queries before deploying to Slack
- **Debugging** — see tool calls and agent reasoning
- **Demos** — show the agent to stakeholders

> **Note:** The web UI is a thin wrapper. All logic lives in the `falk` library — the same code powers the web UI, Slack bot, and CLI.

# Slack Bot

The primary way teams interact with falk in production.

## Setup

### 1. Create a Slack app

Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**.

### 2. Enable Socket Mode

Settings → **Socket Mode** → toggle **ON** → create an App-Level Token with `connections:write` scope.

Copy the `xapp-...` token → `SLACK_APP_TOKEN`.

### 3. Create slash command

Features → **Slash Commands** → **Create New Command**:

| Field | Value |
|-------|-------|
| Command | `/falk` |
| Request URL | `https://example.com` (Socket Mode uses websocket; URL not called) |
| Short Description | Query your data |

### 4. Subscribe to events

Features → **Event Subscriptions** → toggle **ON** → add bot events:

| Event | Why |
|-------|-----|
| `app_mention` | Respond when @mentioned in channels |
| `message.im` | Respond to direct messages |
| `reaction_added` | Track 👍/👎 feedback |

### 5. Set bot token scopes

Features → **OAuth & Permissions** → add:

- `app_mentions:read`
- `chat:write`
- `commands`
- `files:write`
- `im:history`
- `im:read`
- `reactions:read`

Install the app and copy the Bot Token → `SLACK_BOT_TOKEN`.

### 6. Configure `.env`

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

### 7. Run

```bash
falk slack
```

## Production deployment

- **Tokens** — Set via environment variables (never hardcode).
- **Session state** — Set `POSTGRES_URL` in `.env` for persistent session state across restarts.
- **Single process** — Socket Mode is intended for a single active bot process.
- **Docker** — Use the scaffolded `docker-compose.yml` for Slack + Postgres. See [Docker Deployment](/deployment/docker).

## Features

- **Slash command** — `/falk What is our revenue?` works without @mentioning the bot
- **Thread memory** — follow-up questions in the same thread preserve context (see [Memory](/concepts/memory))
- **File uploads** — CSV, Excel, and chart files are uploaded directly to the channel
- **Feedback** — 👍/👎 reactions are sent to Logfire (if configured)

## How feedback works

| Reaction | What happens |
|----------|--------------|
| 👍 | Positive score sent to Logfire (if configured) |
| 👎 | Negative score sent to Logfire (if configured) |

Data stewards review feedback in the Logfire dashboard and update config files. See [Logfire Observability](/deployment/logfire).

## Troubleshooting

| Startup failure | Cause | Fix |
|-----------------|-------|-----|
| `SLACK_BOT_TOKEN` / `SLACK_APP_TOKEN` missing | Tokens not set in `.env` | Add both tokens to `.env` |
| `Cannot start Slack bot - session config invalid` | Session store misconfigured | Set `session.store=memory` or add `POSTGRES_URL` for Postgres |
| `DataAgent initialization failed` | Invalid project config or warehouse | Check `falk_project.yaml`, `semantic_models.yaml`, and database connection |

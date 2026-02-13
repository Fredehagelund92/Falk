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
- `commands` — for /falk slash command
- `files:write` — upload CSV, Excel, chart files
- `im:history`
- `im:read`
- `reactions:read`

Install the app and copy the Bot Token → `SLACK_BOT_TOKEN`.

### 6. Configure `.env`

```bash
SLACK_BOT_TOKEN=xoxb-...   # OAuth & Permissions → Bot User OAuth Token
SLACK_APP_TOKEN=xapp-...   # Basic Information → App-Level Tokens
```

### 7. Run

```bash
falk slack
```

## Features

- **Slash command** — `/falk What is our revenue?` works without @mentioning the bot
- **Thread memory** — follow-up questions in the same thread preserve context
- **File uploads** — CSV, Excel, and chart files are uploaded directly to the channel
- **Feedback** — 👍/👎 reactions are sent to LangFuse as scores

## How feedback works

When users react to the bot's messages:

| Reaction | What happens |
|----------|--------------|
| 👍 | Positive score sent to LangFuse (if configured) |
| 👎 | Negative score sent to LangFuse (if configured) |

Data stewards review feedback in the LangFuse dashboard, add corrections, and update config files. See [LangFuse Observability](langfuse.md).

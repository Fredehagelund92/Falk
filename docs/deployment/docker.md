# Docker Deployment

Projects created with `falk init` include a `Dockerfile` and `docker-compose.yml` for containerized deployment.

## Single container (Dockerfile)

For a single service (web chat, MCP, or Slack):

```bash
# Build
docker build -t my-falk-project .

# Run (web chat on port 8000)
docker run --env-file .env -p 8000:8000 my-falk-project

# Or override command for MCP or Slack
docker run --env-file .env -p 8000:8000 my-falk-project falk mcp --transport http --host 0.0.0.0 --port 8000
docker run --env-file .env my-falk-project falk slack
```

Ensure `.env` contains your LLM API key, Slack tokens (if using Slack), and `POSTGRES_URL` if you use Postgres for session storage.

## Full stack (docker-compose)

For MCP, Slack, and Postgres session store together:

```bash
cp .env.example .env
# Edit .env: add OPENAI_API_KEY, SLACK_BOT_TOKEN, SLACK_APP_TOKEN, etc.

# Set session.store to postgres in falk_project.yaml (session section)
# docker-compose sets POSTGRES_URL automatically for the postgres service

docker compose up --build
```

This starts:

| Service   | Purpose                          | Port / Notes                    |
|-----------|----------------------------------|---------------------------------|
| `postgres`| Session state (thread memory)    | Internal only                   |
| `mcp`     | HTTP MCP server                  | `http://localhost:8000/mcp`     |
| `slack`   | Slack bot (slash command, DMs)   | Socket Mode (no inbound port)   |

### Run only what you need

```bash
# MCP + Postgres only (no Slack)
docker compose up --build mcp

# Slack + Postgres only (no MCP)
docker compose up --build slack
```

### Production notes

- **Session store**: Set `session.store: postgres` in `falk_project.yaml` when using the compose stack. The `postgres` service and `POSTGRES_URL` are configured by the compose file.
- **Slack**: Only one Slack bot process should run. Use `docker compose up slack` (or scale mcp separately).
- **External Postgres**: To use your own Postgres, set `POSTGRES_URL` in `.env` and remove the `postgres` service from `docker-compose.yml`.
- **Secrets**: Never commit `.env`. Use env vars or a secrets manager in production.

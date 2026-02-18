<img height="150" alt="tt" src="https://github.com/user-attachments/assets/ab3b7519-06a6-4ddd-9c2c-aa707daed224" />


*Governed AI access to your data warehouse, powered by semantic layers.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## What is falk?

falk is a data agent that queries your warehouse using **governed metrics** from your semantic layer. Define metrics once in YAML, query naturally through Slack, web UI, or any MCP client. Same numbers everywhere.

**Key features:**

- **Governed access** — Only approved metrics, not raw SQL
- **MCP server** — Standard protocol for AI tools (Cursor, Claude Desktop, any MCP client)
- **Multi-interface** — MCP server, Slack bot, web UI
- **Observable** — LangFuse tracing, feedback collection, YAML-based evals
- **Multi-LLM** — OpenAI, Anthropic, Gemini (via Pydantic AI)

---

## Quick Start

```bash
# Install
pip install falk

# Or with optional features
pip install "falk[slack,langfuse,charts]"
pip install "falk[all]"  # Everything  # or: git clone + uv sync

# Create a project with sample data
falk init my-project
cd my-project

# Add your API key
cp .env.example .env
# Edit .env: OPENAI_API_KEY=sk-...

# Validate configuration
falk test --fast

# Option 1: Start MCP server (connect from Cursor, Claude Desktop)
falk mcp

# Option 2: Start web UI
falk chat  # → http://localhost:8000

# Option 3: Start Slack bot
falk slack
```

---

## Example: Using falk from Cursor

Connect Cursor to falk's MCP server and query naturally:

```
You: "Show me revenue by region"
→ falk uses governed metrics, returns structured data

You: "Compare revenue this month vs last"
→ falk uses compare_periods and returns current vs previous period
```

No manual drilling. Instant root cause analysis. Same experience in Slack, web UI, or any MCP client.

---

## Documentation

📖 **[Full documentation →](https://fredehagelund92.github.io/Falk/)**

- [Quick Start](https://fredehagelund92.github.io/Falk/getting-started/quickstart/)
- [Slack Bot Setup](https://fredehagelund92.github.io/Falk/deployment/slack/)
- [Configuration Guide](https://fredehagelund92.github.io/Falk/configuration/)
- [CLI Reference](https://fredehagelund92.github.io/Falk/cli-reference/)

---

## Requirements

- Python 3.11+
- OpenAI, Anthropic, or Google API key
- DuckDB (included) or Snowflake/BigQuery/PostgreSQL

---

## Contributing

See [Contributing Guide](https://fredehagelund92.github.io/Falk/contributing/) for guidelines.

---

## Inspiration & Credits

falk was inspired by:

- [OpenAI's in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/) — grounded metric querying
- [nao](https://github.com/getnao/nao) — context engineering and agent reliability
- [dash](https://github.com/agno-agi/dash) — self-learning from feedback

---

## Built With

[Pydantic AI](https://github.com/pydantic/pydantic-ai) · [Boring Semantic Layer](https://github.com/boringdata/boring-semantic-layer) · [DuckDB](https://duckdb.org/) · [LangFuse](https://langfuse.com/)

---

## License

MIT — see [LICENSE](LICENSE).

# LLM Providers

falk supports multiple LLM providers through Pydantic AI. Choose the provider that best fits your needs.

## Supported providers

| Provider | Model format | API key env var | Example models |
|----------|--------------|-----------------|----------------|
| **OpenAI** | `openai:MODEL` | `OPENAI_API_KEY` | `gpt-5-mini`, `gpt-5`, `gpt-5.2` |
| **Anthropic** | `anthropic:MODEL` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-20241022`, `claude-3-opus`, `claude-3-haiku` |
| **Google** | `google-genai:MODEL` | `GOOGLE_API_KEY` | `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-pro` |

## Configuration

### 1. Set provider and model

In `falk_project.yaml`:

```yaml
agent:
  provider: openai   # openai, anthropic, gemini, mistral
  model: gpt-5-mini # or gpt-5.2, claude-3-5-sonnet-20241022, gemini-1.5-pro, etc.
```

### 2. Set your API key

In `.env`:

```bash
# For OpenAI
OPENAI_API_KEY=sk-...

# For Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# For Google
GOOGLE_API_KEY=...
```

## Model selection guide

**Cost-effective:** `gpt-5-mini`, `claude-3-haiku`, `gemini-1.5-flash`

**Balanced:** `gpt-5`, `claude-3-5-sonnet`, `gemini-1.5-pro`

**Best quality:** `gpt-5.2`, `claude-3-opus`, `gemini-1.5-pro`

## Troubleshooting

**"No API key found"** — Make sure you've set the correct API key for your chosen provider in `.env`.

**"Model not found"** — Verify the model name is correct for your provider. Check [Pydantic AI Models Reference](https://ai.pydantic.dev/api/models/base/).

**"Provider not supported"** — Ensure you have the latest version of `pydantic-ai-slim`. Some providers may require additional dependencies.

## See also

- [Installation Guide](/getting-started/installation) — Setup instructions

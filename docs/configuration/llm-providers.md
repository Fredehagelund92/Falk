# LLM Providers

falk supports multiple LLM providers through Pydantic AI. Choose the provider that best fits your needs.

## Supported Providers

| Provider | Model Format | API Key Env Var | Example Models |
|---|---|---|---|
| **OpenAI** | `openai:MODEL` | `OPENAI_API_KEY` | `gpt-5-mini`, `gpt-5`, `gpt-5.2` |
| **Anthropic** | `anthropic:MODEL` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-20241022`, `claude-3-opus`, `claude-3-haiku` |
| **Google** | `google-genai:MODEL` | `GOOGLE_API_KEY` | `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-pro` |

## Configuration

### 1. Set Provider and Model

Set `agent.provider` and `agent.model` in `falk_project.yaml`:

```yaml
agent:
  provider: openai   # openai, anthropic, gemini, mistral
  model: gpt-5-mini  # or gpt-5.2, claude-3-5-sonnet-20241022, gemini-1.5-pro, etc.
```

### 2. Set Your API Key

Set the API key for your chosen provider:

```bash
# For OpenAI
OPENAI_API_KEY=sk-...

# For Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# For Google
GOOGLE_API_KEY=...
```

## Model Selection Guide

**Cost-effective:**
- OpenAI: `gpt-5-mini`
- Anthropic: `claude-3-haiku`
- Google: `gemini-1.5-flash`

**Balanced:**
- OpenAI: `gpt-5`
- Anthropic: `claude-3-5-sonnet`
- Google: `gemini-1.5-pro`

**Best quality:**
- OpenAI: `gpt-5.2`
- Anthropic: `claude-3-opus`
- Google: `gemini-1.5-pro` (latest)

## Provider-Specific Notes

### OpenAI

- Fast and reliable
- Good tool calling support
- Default choice for most use cases

### Anthropic Claude

- Excellent reasoning capabilities
- Great for complex analytical queries
- Strong instruction following

### Google Gemini

- Good multilingual support
- Competitive pricing
- Fast response times

## Troubleshooting

**"No API key found"**
- Make sure you've set the correct API key for your chosen provider
- Check that the key is in your `.env` file or environment

**"Model not found"**
- Verify the model name is correct for your provider
- Check Pydantic AI docs for the latest model names

**"Provider not supported"**
- Ensure you have the latest version of `pydantic-ai-slim`
- Some providers may require additional dependencies

## See Also

- [Pydantic AI Models Reference](https://ai.pydantic.dev/api/models/base/) — Complete list of all supported models and providers
- [Pydantic AI Documentation](https://ai.pydantic.dev/) — General Pydantic AI documentation
- [Installation Guide](../getting-started/installation.md) — Setup instructions


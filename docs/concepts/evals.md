# Testing & Validation

Validate your project configuration, semantic models, and test that your agent gives correct answers.

## `falk validate` vs `falk test`

`falk validate` runs project/runtime checks:

1. **Configuration validation** - Checks `falk_project.yaml` structure and required fields
2. **Semantic layer validation** - Validates BSL models for errors, duplicates, missing fields
3. **Connection test** - Verifies warehouse connectivity (optional with `--no-connection`)
4. **Agent initialization** - Ensures agent can be built with current config

`falk test` runs behavior eval cases from `evals/`.

Every time you update `semantic_models.yaml`, `RULES.md`, or context files, run `falk validate` first, then `falk test` for behavior checks.

## Test cases (YAML)

Define test cases in `evals/`:

```yaml
# evals/basic.yaml
- question: "What's our total revenue?"
  expected_tools:
    - query_metric
  expected_contains:
    - "revenue"
  expected_not_contains:
    - "I don't know"

- question: "Show me revenue by region"
  expected_tools:
    - query_metric
  expected_kwargs:
    group_by: ["region"]
```

Each test case specifies:
- **question** — what the user asks
- **expected_tools** — which tools should be called
- **expected_contains** — strings that should appear in the response
- **expected_not_contains** — strings that should NOT appear
- **expected_kwargs** — expected arguments to tool calls

## Running evals

```bash
# Validate project/runtime
falk validate

# Quick validation only (no connection test, no agent init)
falk validate --fast

# Run all evals
falk test

# Filter eval files
falk test --pattern "*.yaml"

# Verbose output
falk test --verbose

# Filter by tags
falk test --tags access,gotchas
```

## Writing good test cases

### Start with real questions

The best test cases come from actual user questions (especially ones that went wrong):

```yaml
# This failed before we added the "sales" synonym
- question: "What are our total sales?"
  expected_tools:
    - query_metric
  expected_contains:
    - "revenue"
```

### Cover edge cases

```yaml
# Gotcha awareness
- question: "What was revenue yesterday?"
  expected_contains:
    - "delay"  # Should mention the 48-hour delay

# Entity resolution
- question: "Revenue for acme"
  expected_tools:
    - lookup_values
    - query_metric
```

### Keep it focused

Each test case should test ONE thing. Don't write tests that check everything at once.

## Pydantic Evals integration

For more advanced testing, falk includes a bridge to [Pydantic Evals](https://ai.pydantic.dev/evals/):

```python
from falk.evals.pydantic_adapter import to_pydantic_evals_dataset
from falk.evals.cases import load_cases

cases = load_cases("evals/basic.yaml")
dataset = to_pydantic_evals_dataset(cases)
```

This lets you use Pydantic Evals' richer assertion system alongside the YAML-based cases.

## CI integration

Add evals to your CI pipeline:

```yaml
# .github/workflows/evals.yml
name: Run Evals
on: [pull_request]

jobs:
  evals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e .
      - run: falk test --verbose
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## LangFuse for production evaluation

For production, use LangFuse's LLM-as-a-judge evaluations:

- Evals (YAML) → local testing, CI, regression catching
- LangFuse → production monitoring, feedback analysis, prompt evaluation

See [LangFuse Observability](../deployment/langfuse.md) for setup.

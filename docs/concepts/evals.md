# Testing & Validation

Validate your project configuration and test that your agent gives correct answers.

## `falk validate` vs `falk test`

**`falk validate`** runs project/runtime checks:

1. Configuration validation — checks `falk_project.yaml` structure
2. Semantic layer validation — validates BSL models for errors, duplicates, missing fields
3. Connection test — verifies warehouse connectivity (optional with `--no-connection`)
4. Agent initialization — ensures agent can be built with current config

**`falk test`** runs behavior eval cases from `evals/`.

Run `falk validate` first, then `falk test` whenever you update `semantic_models.yaml`, `RULES.md`, or context files.

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
falk validate
falk validate --fast   # Quick validation only
falk test
falk test --pattern "*.yaml"
falk test --verbose
falk test --tags access,gotchas
```

## Writing good test cases

### Start with real questions

The best test cases come from actual user questions (especially ones that went wrong):

```yaml
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
    - "delay"

# Entity resolution
- question: "Revenue for acme"
  expected_tools:
    - lookup_values
    - query_metric
```

### Keep it focused

Each test case should test ONE thing.

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

## See also

- [Logfire Observability](/deployment/logfire) — production monitoring and feedback

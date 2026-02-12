# Agent Skills

The `falk` CLI is designed to be called by **other agents, workflows, and automation**. Every command supports `--json` for machine-readable output.

## Why CLI for skills?

- **Universal** — any agent can shell out to a CLI
- **Stable contract** — clear inputs/outputs, versioned, testable
- **CI/CD ready** — works in GitHub Actions, Airflow, cron
- **No lock-in** — works with any orchestrator (LangGraph, CrewAI, Claude, etc.)

## Core primitives

### Query metrics

```bash
falk query revenue --group-by region --json
```

```json
{
  "ok": true,
  "metric": "revenue",
  "rows": [
    {"region": "US", "revenue": 1000000},
    {"region": "EU", "revenue": 750000}
  ]
}
```

### Decompose (root cause)

```bash
falk decompose revenue --period month --json
```

### Lookup dimension values

```bash
falk lookup customer --search "acme" --json
```

### Compare periods

```bash
falk compare revenue --period month --group-by region --json
```

### Explore metadata

```bash
falk metrics list --json
falk metrics describe revenue --json
falk dimensions list --json
```

## Example: Python skill

```python
import subprocess, json

def query_metric(metric: str, group_by: str | None = None) -> dict:
    cmd = ["falk", "query", metric, "--json"]
    if group_by:
        cmd += ["-g", group_by]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

data = query_metric("revenue", "region")
if data["ok"]:
    for row in data["rows"]:
        print(f"{row['region']}: ${row['revenue']:,.0f}")
```

## Example: Alert skill

```python
import subprocess, json

def check_revenue_drops():
    result = subprocess.run(
        ["falk", "compare", "revenue", "--period", "week", "-g", "region", "--json"],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)

    alerts = []
    for row in data.get("deltas", []):
        if row.get("pct_change", 0) < -15:
            alerts.append(f"⚠️ {row['region']}: {row['pct_change']:.1f}%")

    return alerts or ["✅ All regions within normal range"]
```

## Example: GitHub Actions

```yaml
name: Daily Revenue Report
on:
  schedule:
    - cron: '0 9 * * *'
jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e .
      - run: falk compare revenue --period day --json > report.json
```

## Error handling

All commands return exit code 0 on success, 1 on failure. With `--json`, errors are structured:

```python
result = subprocess.run(["falk", "query", "revenue", "--json"], ...)
if result.returncode != 0:
    error = json.loads(result.stdout)
    print(f"Error: {error.get('error')}")
```

## Tips

1. **Always use `--json`** for skills
2. **Check exit codes** before parsing
3. **Use `lookup`** before filtering to avoid typos
4. **Limit rows** with `--limit` to keep outputs manageable

## Related

- [CLI Reference](../cli-reference.md) — all commands and options
- [Evaluation Framework](evals.md) — test your skills
- [Agent Tools](tools.md) — tools available inside the agent

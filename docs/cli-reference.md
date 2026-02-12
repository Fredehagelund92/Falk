# CLI Reference

Run `falk --help` or `falk <command> --help` for the latest options.

---

## `falk init`

Scaffold a new falk project.

```bash
falk init my-project
falk init my-project --template ecommerce
```

Creates: `RULES.md`, `knowledge/`, `semantic_models.yaml`, `falk_project.yaml`, `.env.example`, and sample data.

---

## `falk sync`

Validate configuration.

```bash
falk sync
falk sync --verbose
```

Checks project root, config files, semantic models, database, and skills (if enabled).

---

## `falk query`

Query a metric from the warehouse.

```bash
falk query revenue
falk query revenue -g region
falk query revenue -g region -f region=US --order desc --limit 10
falk query revenue --json
```

| Option | Short | Description |
|--------|-------|-------------|
| `--group-by` | `-g` | Group by dimensions |
| `--filter` | `-f` | Filter as `dim=value` |
| `--time-grain` | `-t` | `day`, `week`, `month`, `quarter`, `year` |
| `--order` | | `asc` or `desc` by metric |
| `--limit` | `-n` | Max rows |
| `--json` | | JSON output |

---

## `falk decompose`

Root cause analysis — explain *why* a metric changed.

```bash
falk decompose revenue
falk decompose revenue --period month
falk decompose revenue --filter "region=North America"
falk decompose revenue --json
```

| Option | Description |
|--------|-------------|
| `--period` | `week`, `month`, or `quarter` (default: `month`) |
| `--filter` | Filter as `dim=value` |
| `--json` | JSON output |

---

## `falk lookup`

Fuzzy-search dimension values.

```bash
falk lookup customer_name --search "acme"
falk lookup region --json
```

---

## `falk compare`

Compare a metric across periods.

```bash
falk compare revenue --period month
falk compare revenue --period week --filter "region=US"
```

---

## `falk export`

Export query results to file.

```bash
falk export revenue -g region -o revenue.csv
falk export revenue -g region -o revenue.json
```

Format is inferred from the file extension.

---

## `falk metrics list`

List all available metrics.

```bash
falk metrics list
falk metrics list --json
```

## `falk metrics describe`

Get details about a specific metric.

```bash
falk metrics describe revenue
falk metrics describe revenue --json
```

---

## `falk dimensions list`

List all available dimensions.

```bash
falk dimensions list
falk dimensions list --json
```

## `falk dimensions describe`

Get details about a specific dimension.

```bash
falk dimensions describe region
```

---

## `falk config`

Show current configuration.

```bash
falk config
falk config --json
```

---

## `falk evals`

Run evaluation test cases.

```bash
falk evals evals/basic.yaml
falk evals evals/ --json
```

---

## `falk chat`

Start the web UI server.

```bash
falk chat                    # default: port 8000
falk chat --port 3000        # custom port
falk chat --no-reload        # disable auto-reload
```

---

## `falk slack`

Start the Slack bot.

```bash
falk slack
```

Requires `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` in `.env`.

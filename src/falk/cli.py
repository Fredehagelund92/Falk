"""falk CLI - Primary interface for querying, exploring, and running falk.

This CLI exposes falk's core capabilities:
- Query metrics from the warehouse
- Explore available metrics and dimensions
- Lookup dimension values
- Compare periods
- Decompose metric changes (root cause analysis)
- Export data
- Run evaluations
- Start servers (chat, slack)

Designed for:
- Agent skills (use --json for machine-readable output)
- CI/CD pipelines
- Developer workflows
- Direct human use (pretty text by default)
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

import typer

from falk.agent import DataAgent
from falk.evals.cases import discover_cases, load_cases
from falk.evals.runner import run_evals
from falk.tools.warehouse import lookup_dimension_values, run_warehouse_query

app = typer.Typer(help="falk CLI - Query metrics, explore dimensions, run evals")


# ---------------------------------------------------------------------------
# Configuration & Validation
# ---------------------------------------------------------------------------


@app.command()
def sync(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed configuration",
    ),
) -> None:
    """Validate and sync falk configuration.
    
    This command:
    - Finds project root
    - Loads and validates falk_project.yaml
    - Loads and validates semantic_models.yaml (BSL)
    - Checks extension connectivity (LangFuse, Slack, etc.)
    - Reports configuration status
    
    Example:
        falk sync
        falk sync --verbose
    """
    from falk.settings import load_settings
    from falk.agent import DataAgent
    
    typer.echo("🔄 Syncing falk configuration...\n")
    
    try:
        # Load settings
        settings = load_settings()
        typer.echo(f"✓ Project root: {settings.project_root}")
        
        # Check semantic models
        if settings.bsl_models_path.exists():
            agent = DataAgent()
            metrics = agent.list_metrics()
            models = metrics.get("semantic_models", {})
            total_metrics = sum(len(m) for m in models.values())
            total_dims = len(agent.dimension_descriptions)
            
            typer.echo(f"✓ Semantic models: {len(models)} models, {total_metrics} metrics, {total_dims} dimensions")
            
            if verbose:
                for model_name, measures in models.items():
                    typer.echo(f"  - {model_name}: {len(measures)} metrics")
        else:
            typer.echo(f"⚠️  Semantic models not found: {settings.bsl_models_path}", err=True)
        
        # Check profile
        conn = settings.connection
        typer.echo(f"✓ Connection: {conn.get('type', '?')} ({conn.get('database', conn.get('project_id', '—'))})")
        
        # Check agent config
        typer.echo(f"✓ Agent: {settings.agent.provider}/{settings.agent.model}")
        if verbose:
            typer.echo(f"  - Auto-run: {settings.advanced.auto_run}")
            typer.echo(f"  - Examples: {len(settings.agent.examples)}")
            typer.echo(f"  - Rules: {len(settings.agent.rules)}")
        
        # Check extensions
        typer.echo("\n📦 Extensions:")
        for name, ext in settings.extensions.items():
            status = "enabled" if ext.enabled else "disabled"
            icon = "✓" if ext.enabled else "○"
            typer.echo(f"{icon} {name}: {status}")
            
            # Check connectivity for enabled extensions
            if ext.enabled and name == "langfuse":
                import os
                if os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"):
                    typer.echo("  - API keys: configured")
                else:
                    typer.echo("  - ⚠️  API keys not found in environment", err=True)
            
            if ext.enabled and name == "slack":
                import os
                if os.getenv("SLACK_BOT_TOKEN") and os.getenv("SLACK_APP_TOKEN"):
                    typer.echo("  - Tokens: configured")
                else:
                    typer.echo("  - ⚠️  Tokens not found in environment", err=True)
        
        # Check access control
        if settings.access_policy_path:
            typer.echo(f"\n🔒 Access policy: {settings.access_policy_path.name}")
        
        # Check skills (if enabled)
        if settings.skills.enabled:
            for d in settings.skills.directories:
                skills_dir = settings.project_root / d
                if skills_dir.exists():
                    typer.echo(f"\n🔧 Skills: {d}")
                else:
                    typer.echo(f"\n🔧 Skills: {d} (directory not found - add SKILL.md files)")
        
        typer.echo("\n✅ Configuration valid!")
        
    except Exception as e:
        typer.echo(f"\n❌ Configuration error: {e}", err=True)
        import traceback
        if verbose:
            traceback.print_exc()
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Project Initialization
# ---------------------------------------------------------------------------


def _copy_scaffold(src: Path, dst: Path) -> None:
    """Copy a file from the scaffold directory, creating parent dirs as needed."""
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)


def _copy_scaffold_dir(src_dir: Path, dst_dir: Path) -> None:
    """Copy a directory tree from scaffold."""
    if not src_dir.exists():
        return
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)


@app.command()
def init(
    project_name: Optional[str] = typer.Argument(
        None,
        help="Project directory name, or '.' to init in current directory (default: current dir)",
    ),
    template: str = typer.Option(
        "ecommerce",
        "--template",
        "-t",
        help="Project template: 'ecommerce', 'saas', 'minimal'",
    ),
) -> None:
    """Initialize a new falk project with complete structure.
    
    Creates a new directory with:
    - RULES.md (agent behavior - included in every conversation)
    - knowledge/ (business terms, data quality gotchas)
      - business.md (glossary, company context)
      - gotchas.md (known issues, caveats)
    - semantic_models.yaml (BSL - metrics & dimensions)
    - falk_project.yaml (LLM, extensions, access control)
    - data/warehouse.duckdb (sample data)
    - .env.example (environment variables)
    - README.md (getting started guide)
    
    Examples:
        falk init                    # Init in current directory
        falk init .                  # Init in current directory
        falk init my-analytics-project   # Create new subdirectory
    """
    cwd = Path.cwd()
    if project_name is None or project_name == ".":
        # Init in current directory
        project_path = cwd
        display_name = cwd.name
        # Check if already a falk project
        if (project_path / "semantic_models.yaml").exists() or (
            project_path / "falk_project.yaml"
        ).exists() or (project_path / "RULES.md").exists():
            typer.echo(
                "❌ Current directory already contains a falk project.",
                err=True,
            )
            typer.echo(
                "   Remove semantic_models.yaml, falk_project.yaml and RULES.md to re-initialize, or use 'falk init my-project' to create a new subdirectory.",
                err=True,
            )
            raise typer.Exit(code=1)
    else:
        # Create new subdirectory
        project_path = cwd / project_name
        display_name = project_name
        if project_path.exists():
            typer.echo(f"❌ Directory '{project_name}' already exists", err=True)
            raise typer.Exit(code=1)
    
    typer.echo(f"📦 Creating new falk project: {display_name}")
    typer.echo(f"   Template: {template}")
    
    # Create directory structure (may already exist when init in cwd)
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "knowledge").mkdir()
    (project_path / "data").mkdir()
    (project_path / "evals").mkdir()
    
    # Scaffold directory ships with the falk package
    scaffold_dir = Path(__file__).parent / "scaffold"
    
    if not scaffold_dir.exists():
        typer.echo("❌ Scaffold directory not found in falk package", err=True)
        raise typer.Exit(code=1)
    
    # Copy RULES.md
    _copy_scaffold(scaffold_dir / "RULES.md", project_path / "RULES.md")
    typer.echo("   ✓ Created RULES.md")
    
    # Copy knowledge templates
    for src_file in [
        "knowledge/business.md",
        "knowledge/gotchas.md",
    ]:
        _copy_scaffold(scaffold_dir / src_file, project_path / src_file)
    typer.echo("   ✓ Created knowledge/ directory with templates")

    # Copy config files to project root
    _copy_scaffold(
        scaffold_dir / "semantic_models_ecommerce.yaml",
        project_path / "semantic_models.yaml",
    )
    _copy_scaffold(
        scaffold_dir / "falk_project.yaml",
        project_path / "falk_project.yaml",
    )
    typer.echo("   ✓ Created semantic_models.yaml, falk_project.yaml")

    # Copy eval templates
    for src_file in [
        "evals/basic.yaml",
        "evals/gotchas.yaml",
    ]:
        _copy_scaffold(scaffold_dir / src_file, project_path / src_file)
    typer.echo("   ✓ Created evals/ with basic test cases")

    # Copy skills directory (pydantic-ai-skills)
    skills_src = scaffold_dir / "skills"
    if skills_src.exists():
        _copy_scaffold_dir(skills_src, project_path / "skills")
        typer.echo("   ✓ Created skills/ with example skill (enable in falk_project.yaml)")
    
    # Create .env.example
    env_example = """# LLM API Keys (choose one)
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=...

# Optional: LangFuse observability
# LANGFUSE_PUBLIC_KEY=pk-...
# LANGFUSE_SECRET_KEY=sk-...
# LANGFUSE_HOST=https://cloud.langfuse.com
"""
    (project_path / ".env.example").write_text(env_example, encoding="utf-8")
    typer.echo("   ✓ Created .env.example")
    
    # Create project README
    project_readme = f"""# {display_name}

A falk project for natural language data queries powered by your semantic layer.

## 🚀 Quick Start

1. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your LLM API key (OPENAI_API_KEY or ANTHROPIC_API_KEY)
   ```

2. **Verify configuration:**
   ```bash
   falk sync
   ```

3. **Query your data:**
   ```bash
   falk query revenue --json
   falk metrics list --json
   falk query revenue --group-by region --limit 10
   ```

## 📁 Project Structure

```
{display_name}/
├── RULES.md                          # Agent behavior (always included)
├── knowledge/                        # Business terms, data quality gotchas
│   ├── business.md                  # Business terms & company context
│   └── gotchas.md                   # Known data issues, caveats
├── semantic_models.yaml             # Metrics & dimensions (BSL)
├── falk_project.yaml                # Config (LLM, connection, extensions)
├── skills/                          # Agent skills (optional, enable in config)
├── data/
│   └── warehouse.duckdb             # Your data warehouse
└── .env                              # API keys (create from .env.example)
```

## 🎯 Customization Guide

### 1. Define Your Business Context

**Start here!** Edit these files to teach falk about your business:

- **`RULES.md`** - How agent should behave (tone, SQL style, orchestration)
- **`knowledge/business.md`** - Business terms, company context
- **`knowledge/gotchas.md`** - Data quality issues, caveats

**Why?** These files are sent to the AI to provide context about YOUR business.

### 2. Define Your Data Layer

- **`semantic_models.yaml`** - Define metrics and dimensions using Boring Semantic Layer
  - Metrics: revenue, orders, customers, etc.
  - Dimensions: region, product, customer_segment, etc.
  - SQL mappings to your database tables

### 3. Configure Technical Settings

- **`falk_project.yaml`** - LLM provider, connection (inline), extensions, access control
- **`.env`** - API keys

### 4. Document Data Quality

- **`knowledge/gotchas.md`** - Known issues, data freshness, caveats
  - Helps agent provide accurate answers
  - Sets proper expectations for users

## 💡 Context Engineering

falk uses a **context-first** approach:

**RULES.md** is included with EVERY message:
- Keep it concise (tone, style, orchestration)
- Use it to point to detailed domain files

**knowledge/** directory for detailed knowledge:
- Only loaded when relevant (token-efficient)
- business.md: terms, company context
- gotchas.md: data quality notes

**Example orchestration in RULES.md:**
```markdown
## Orchestration - Domain Context
For business context: Read `knowledge/business.md`
For data quality notes: Read `knowledge/gotchas.md`
```

## 🔧 Usage Examples

```bash
# Validate and sync configuration
falk sync --verbose

# Query metrics
falk query revenue
falk query revenue --group-by region
falk query orders --filter status=paid --limit 100

# Explore available metrics
falk metrics list
falk metrics describe revenue

# Explore dimensions
falk dimensions list
falk dimensions values region

# JSON output (for agent skills / automation)
falk query revenue --group-by region --json
```

## 📚 Documentation

- Full documentation: https://github.com/yourusername/falk
- Boring Semantic Layer: https://github.com/pleonex/boring-semantic-layer

## 🤝 Contributing

1. Edit `knowledge/` files to improve agent knowledge
2. Update `semantic_models.yaml` to add metrics
3. Document data issues in `knowledge/gotchas.md`
4. Test with `falk sync` and example queries
"""
    (project_path / "README.md").write_text(project_readme, encoding="utf-8")
    typer.echo("   ✓ Created README.md")
    
    # Create sample data
    try:
        seed_script = scaffold_dir / "seed_data.py"
        if seed_script.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("seed_data", seed_script)
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            mod.create_example_database(project_path / "data" / "warehouse.duckdb")
            typer.echo("   ✓ Created sample database")
    except Exception as e:
        typer.echo(f"   ⚠️  Could not create sample data: {e}", err=True)
        typer.echo("   You can manually create it later.")
    
    # Success message
    typer.echo()
    typer.echo(f"✨ Project '{display_name}' created successfully!")
    typer.echo()
    typer.echo("📁 Structure created:")
    typer.echo("  ✓ RULES.md - Agent behavior rules")
    typer.echo("  ✓ knowledge/ - Business terms & data quality gotchas")
    typer.echo("  ✓ semantic_models.yaml, falk_project.yaml - Configuration")
    typer.echo("  ✓ data/ - Data warehouse")
    typer.echo()
    typer.echo("🚀 Next steps:")
    if project_name is None or project_name == ".":
        typer.echo("  1. cp .env.example .env")
        typer.echo("  2. Edit .env and add your LLM API key")
        typer.echo("  3. falk sync  # Validate configuration")
        typer.echo("  4. falk metrics list  # See available metrics")
    else:
        typer.echo(f"  1. cd {project_name}")
        typer.echo("  2. cp .env.example .env")
        typer.echo("  3. Edit .env and add your LLM API key")
        typer.echo("  4. falk sync  # Validate configuration")
        typer.echo("  5. falk metrics list  # See available metrics")
    typer.echo()
    typer.echo("✏️  Customize your agent:")
    typer.echo("  • Edit RULES.md to define agent behavior")
    typer.echo("  • Edit knowledge/business.md with your business context")
    typer.echo("  • Edit knowledge/gotchas.md with data quality notes")
    typer.echo("  • Edit semantic_models.yaml to define metrics")
    typer.echo()
    typer.echo("📖 See README.md for detailed guide")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_agent() -> DataAgent:
    """Get a DataAgent instance."""
    return DataAgent()


def _format_rows_table(rows: list[dict[str, Any]], max_rows: int = 20) -> str:
    """Format rows as a simple text table."""
    if not rows:
        return "No rows."
    
    lines: list[str] = []
    for row in rows[:max_rows]:
        parts = [f"{k}={v}" for k, v in row.items()]
        lines.append("  " + ", ".join(parts))
    if len(rows) > max_rows:
        lines.append(f"  ... ({len(rows) - max_rows} more rows)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core: Query
# ---------------------------------------------------------------------------


@app.command()
def query(
    metric: str = typer.Argument(..., help="Metric name to query."),
    group_by: Optional[list[str]] = typer.Option(
        None,
        "--group-by",
        "-g",
        help="Group-by dimensions (repeatable). Example: -g region -g product",
    ),
    filter_dim: Optional[list[str]] = typer.Option(
        None,
        "--filter",
        "-f",
        help='Filter as "dim=value" (repeatable). Example: -f region=US -f status=active',
    ),
    time_grain: Optional[str] = typer.Option(
        None,
        "--time-grain",
        "-t",
        help='Time grain: "day", "week", "month", "quarter", "year".',
    ),
    order: Optional[str] = typer.Option(
        None,
        "--order",
        help='Sort order: "asc" or "desc" (sorts by metric value).',
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-n",
        help="Max number of rows to return.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output JSON for agent skills / scripting.",
    ),
) -> None:
    """Query a metric from the warehouse.
    
    Examples:
        # Simple query
        data-agent query revenue
        
        # Group by region
        data-agent query revenue -g region
        
        # Filter to US only
        data-agent query revenue -f region=US
        
        # Top 10 regions by revenue
        data-agent query revenue -g region --order desc --limit 10
        
        # Daily revenue for last month
        data-agent query revenue -t day --limit 30
        
        # JSON output for agent skills
        data-agent query revenue -g region --json
    """
    core = _get_agent()
    
    # Build query object
    query_obj: dict[str, Any] = {"metric": metric}
    if group_by:
        query_obj["dimensions"] = group_by
    if time_grain:
        query_obj["time_grain"] = time_grain
    if order:
        query_obj["order_by"] = order
    if limit:
        query_obj["limit"] = limit
    
    # Parse filters
    if filter_dim:
        filters: list[dict[str, Any]] = []
        for f in filter_dim:
            if "=" not in f:
                typer.echo(f"❌ Invalid filter format '{f}'. Use 'dimension=value'", err=True)
                raise typer.Exit(code=1)
            dim, val = f.split("=", 1)
            filters.append({"dimension": dim.strip(), "op": "=", "value": val.strip()})
        query_obj["filters"] = filters
    
    # Execute
    result = run_warehouse_query(
        bsl_models=core.bsl_models,
        query_object=query_obj,
    )
    
    # JSON output
    if json_out:
        payload = {
            "ok": result.ok,
            "error": result.error,
            "metric": metric,
            "rows": result.data,
            "count": len(result.data) if result.data else 0,
        }
        typer.echo(json.dumps(payload, default=str))
        if not result.ok:
            raise typer.Exit(code=1)
        return
    
    # Human output
    if not result.ok:
        typer.echo(f"❌ Query failed: {result.error}")
        raise typer.Exit(code=1)
    
    rows = result.data or []
    typer.echo(f"✅ {len(rows)} row(s) for metric '{metric}'" + (f" grouped by {', '.join(group_by)}" if group_by else ""))
    if rows:
        typer.echo("")
        typer.echo(_format_rows_table(rows))


# ---------------------------------------------------------------------------
# Core: Lookup dimension values
# ---------------------------------------------------------------------------


@app.command()
def lookup(
    dimension: str = typer.Argument(..., help="Dimension name."),
    search: Optional[str] = typer.Option(
        None,
        "--search",
        "-s",
        help="Search term (case-insensitive partial match).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output JSON for agent skills / scripting.",
    ),
) -> None:
    """Look up actual values for a dimension (fuzzy search).
    
    Use this before filtering to find exact warehouse values.
    
    Examples:
        # List all regions
        data-agent lookup region
        
        # Search for partners matching "bet"
        data-agent lookup partner --search bet
        
        # JSON output
        data-agent lookup region --json
    """
    core = _get_agent()
    
    try:
        values = lookup_dimension_values(
            bsl_models=core.bsl_models,
            dimension=dimension,
            search=search,
        )
    except Exception as e:
        typer.echo(f"❌ Lookup failed: {e}", err=True)
        raise typer.Exit(code=1)
    
    if values is None:
        typer.echo(f"❌ Dimension '{dimension}' not found.", err=True)
        typer.echo("Use 'data-agent dimensions list' to see available dimensions.")
        raise typer.Exit(code=1)
    
    if json_out:
        typer.echo(json.dumps({"dimension": dimension, "values": values}, default=str))
        return
    
    if not values:
        msg = f"No values found for '{dimension}'"
        if search:
            msg += f" matching '{search}'"
        typer.echo(f"⚠️  {msg}")
        return
    
    header = f"Found {len(values)} value(s) for '{dimension}'"
    if search:
        header += f" matching '{search}'"
    typer.echo(header + ":")
    for v in values:
        typer.echo(f"  • {v}")


# ---------------------------------------------------------------------------
# Core: Compare periods
# ---------------------------------------------------------------------------


@app.command()
def compare(
    metric: str = typer.Argument(..., help="Metric name to compare."),
    period: str = typer.Option(
        "month",
        "--period",
        "-p",
        help='Period: "day" (today vs yesterday), "week", "month", "quarter".',
    ),
    group_by: Optional[list[str]] = typer.Option(
        None,
        "--group-by",
        "-g",
        help="Group-by dimensions (repeatable).",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-n",
        help="Max rows (for top N comparisons).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output JSON for agent skills / scripting.",
    ),
) -> None:
    """Compare a metric between current and previous period.
    
    Examples:
        # This month vs last month
        data-agent compare revenue --period month
        
        # Compare by region
        data-agent compare revenue -p week -g region
        
        # Top 10 regions, current vs previous
        data-agent compare revenue -p month -g region -n 10
    """
    from falk.tools.calculations import compute_deltas, period_date_ranges
    
    core = _get_agent()
    
    try:
        (cur_start, cur_end), (prev_start, prev_end) = period_date_ranges(period)
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(code=1)
    
    def _run(start: str, end: str) -> Any:
        q: dict[str, Any] = {
            "metric": metric,
            "filters": [
                {"dimension": "date", "op": ">=", "value": start},
                {"dimension": "date", "op": "<=", "value": end},
            ],
        }
        if group_by:
            q["dimensions"] = group_by
        if limit:
            q["order_by"] = "desc"
            q["limit"] = limit
        return run_warehouse_query(
            bsl_models=core.bsl_models,
            query_object=q,
        )
    
    cur_result = _run(cur_start, cur_end)
    prev_result = _run(prev_start, prev_end)
    
    if not cur_result.ok:
        typer.echo(f"❌ Query failed (current): {cur_result.error}", err=True)
        raise typer.Exit(code=1)
    if not prev_result.ok:
        typer.echo(f"❌ Query failed (previous): {prev_result.error}", err=True)
        raise typer.Exit(code=1)
    
    cur_data = cur_result.data or []
    prev_data = prev_result.data or []
    
    if not cur_data:
        typer.echo(f"⚠️  No data for current {period} ({cur_start} to {cur_end})")
        return
    
    keys = group_by or []
    deltas = compute_deltas(cur_data, prev_data, metric, keys)
    
    if json_out:
        typer.echo(json.dumps({"metric": metric, "period": period, "deltas": deltas}, default=str))
        return
    
    # Human output
    period_labels = {
        "day": ("today", "yesterday"),
        "week": ("this week", "last week"),
        "month": ("this month", "last month"),
        "quarter": ("this quarter", "last quarter"),
    }
    cur_label, prev_label = period_labels.get(period, ("current", "previous"))
    
    typer.echo(f"*{metric}* — {cur_label} vs {prev_label} ({cur_start} → {cur_end}):")
    typer.echo("")
    
    for row in deltas[:15]:
        group_parts = [f"{row[k]}" for k in keys if k in row]
        prefix = " | ".join(group_parts) + " — " if group_parts else ""
        
        cur_val = row["current"]
        prev_val = row["previous"]
        delta = row["delta"]
        pct = row.get("pct_change")
        
        arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        delta_str = f"+{delta:,.0f}" if delta > 0 else f"{delta:,.0f}"
        pct_str = f" ({arrow} {abs(pct):.1f}%)" if pct is not None else ""
        
        typer.echo(f"  • {prefix}{cur_val:,.0f} vs {prev_val:,.0f} → {delta_str}{pct_str}")
    
    if len(deltas) > 15:
        typer.echo(f"  ... and {len(deltas) - 15} more")


# ---------------------------------------------------------------------------
# Core: Decompose (Root Cause Analysis)
# ---------------------------------------------------------------------------


@app.command()
def decompose(
    metric: str = typer.Argument(..., help="Metric name to decompose."),
    period: str = typer.Option(
        "month",
        "--period",
        "-p",
        help='Period: "week", "month", or "quarter".',
    ),
    filter_dim: Optional[list[str]] = typer.Option(
        None,
        "--filter",
        "-f",
        help='Filter as "dim=value" (repeatable).',
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON (for agent skills).",
    ),
) -> None:
    """Explain why a metric changed — automatic root cause analysis.
    
    This command answers "why?" questions by:
    1. Comparing current vs previous period
    2. Ranking dimensions by impact (which explains the most variance?)
    3. Drilling into the top dimension to show specific contributors
    
    Examples:
        falk decompose revenue
        falk decompose orders --period week
        falk decompose revenue --filter "region=North America"
        falk decompose revenue --json  # For agent skills
    """
    from falk.tools.warehouse import decompose_metric_change
    
    # Parse filters
    filters = {}
    if filter_dim:
        for f in filter_dim:
            if "=" in f:
                k, v = f.split("=", 1)
                filters[k.strip()] = v.strip()
    
    # Load agent
    agent = DataAgent()
    
    # Run decomposition
    result = decompose_metric_change(
        core=agent,
        metric=metric,
        period=period,
        filters=filters if filters else None,
    )
    
    # JSON output
    if json_out:
        output = {
            "ok": result.ok,
            "metric": result.metric,
            "period": result.period,
            "total_delta": result.total_delta,
            "total_pct_change": result.total_pct_change,
            "current_value": result.current_value,
            "previous_value": result.previous_value,
            "dimension_impacts": result.dimension_impacts,
            "top_dimension": result.top_dimension,
            "top_dimension_breakdown": result.top_dimension_breakdown,
            "error": result.error,
        }
        typer.echo(json.dumps(output, indent=2))
        return
    
    # Human-readable output
    if not result.ok:
        typer.echo(f"❌ Failed to decompose {metric}: {result.error}", err=True)
        raise typer.Exit(1)
    
    # Header
    pct_str = f"{result.total_pct_change:+.1f}%" if result.total_pct_change is not None else "N/A"
    delta_str = f"{result.total_delta:+,.2f}"
    
    typer.echo(f"\n📊 {metric.upper()} DECOMPOSITION ({period} over {period})")
    typer.echo("=" * 60)
    typer.echo(f"\nOverall Change: {delta_str} ({pct_str})")
    typer.echo(f"  Current:  {result.current_value:>12,.2f}")
    typer.echo(f"  Previous: {result.previous_value:>12,.2f}")
    
    # No change case
    if abs(result.total_delta) < 0.01:
        typer.echo("\nℹ️  No significant change detected.")
        return
    
    # Dimension impact ranking
    if result.dimension_impacts:
        typer.echo("\n🔍 Dimension Impact Ranking:")
        typer.echo("   (Which dimension has the biggest single contributor?)\n")
        
        for idx, dim_impact in enumerate(result.dimension_impacts[:5], 1):
            dim_name = dim_impact["dimension"]
            impact_pct = dim_impact["variance_explained_pct"]
            
            indicator = " ← Main driver" if idx == 1 else ""
            typer.echo(f"   {idx}. {dim_name:20s} {impact_pct:>6.1f}% (largest contributor){indicator}")
    
    # Top dimension breakdown
    if result.top_dimension and result.top_dimension_breakdown:
        typer.echo(f"\n📈 Breakdown by {result.top_dimension.upper()}:")
        typer.echo("   (Specific contributors to the change)\n")
        
        for item in result.top_dimension_breakdown[:10]:
            dim_val = item["dimension_value"]
            delta = item["delta"]
            pct_change = item["pct_change"]
            contrib_pct = item.get("contribution_pct", item.get("variance_pct", 0))
            
            delta_str = f"{delta:+,.2f}"
            pct_str = f"{pct_change:+.1f}%" if pct_change is not None else "N/A"
            
            emoji = "🔺" if delta > 0 else "🔻"
            
            typer.echo(
                f"   {emoji} {dim_val:25s} {delta_str:>15s} ({pct_str:>8s}) "
                f"— {contrib_pct:>6.1f}% of total change"
            )
        
        if len(result.top_dimension_breakdown) > 10:
            remaining = len(result.top_dimension_breakdown) - 10
            typer.echo(f"\n   ...and {remaining} more")
    
    typer.echo("\n💡 Key Insight: Use this breakdown to understand what's driving your metric changes.\n")


# ---------------------------------------------------------------------------
# Core: Export
# ---------------------------------------------------------------------------


@app.command()
def export(
    metric: str = typer.Argument(..., help="Metric name to export."),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (default: stdout). Format inferred from extension (.csv, .json).",
    ),
    group_by: Optional[list[str]] = typer.Option(
        None,
        "--group-by",
        "-g",
        help="Group-by dimensions (repeatable).",
    ),
    filter_dim: Optional[list[str]] = typer.Option(
        None,
        "--filter",
        "-f",
        help='Filter as "dim=value" (repeatable).',
    ),
    time_grain: Optional[str] = typer.Option(
        None,
        "--time-grain",
        help='Time grain: "day", "week", "month".',
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Max rows.",
    ),
) -> None:
    """Export query results to CSV or JSON.
    
    Examples:
        # Export to CSV
        data-agent export revenue -g region -o revenue.csv
        
        # Export to JSON
        data-agent export revenue -t day -o revenue.json
        
        # Print to stdout (JSON)
        data-agent export revenue -g region
    """
    core = _get_agent()
    
    # Build query
    query_obj: dict[str, Any] = {"metric": metric}
    if group_by:
        query_obj["dimensions"] = group_by
    if time_grain:
        query_obj["time_grain"] = time_grain
    if limit:
        query_obj["limit"] = limit
    
    # Parse filters
    if filter_dim:
        filters: list[dict[str, Any]] = []
        for f in filter_dim:
            if "=" not in f:
                typer.echo(f"❌ Invalid filter '{f}'", err=True)
                raise typer.Exit(code=1)
            dim, val = f.split("=", 1)
            filters.append({"dimension": dim.strip(), "op": "=", "value": val.strip()})
        query_obj["filters"] = filters
    
    result = run_warehouse_query(
        bsl_models=core.bsl_models,
        query_object=query_obj,
    )
    
    if not result.ok:
        typer.echo(f"❌ Query failed: {result.error}", err=True)
        raise typer.Exit(code=1)
    
    rows = result.data or []
    if not rows:
        typer.echo("⚠️  No data to export.")
        return
    
    # Determine format
    if output:
        path = Path(output)
        if path.suffix.lower() == ".csv":
            # CSV
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            typer.echo(f"✅ Exported {len(rows)} rows to {path}")
        else:
            # JSON
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2, default=str)
            typer.echo(f"✅ Exported {len(rows)} rows to {path}")
    else:
        # stdout (JSON)
        json.dump(rows, sys.stdout, default=str)
        sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# Metadata: metrics
# ---------------------------------------------------------------------------


metrics_app = typer.Typer(help="Explore available metrics")
app.add_typer(metrics_app, name="metrics")


@metrics_app.command("list")
def metrics_list(
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output JSON for agent skills / scripting.",
    ),
) -> None:
    """List all available metrics.
    
    Examples:
        # Human-readable list
        data-agent metrics list
        
        # JSON for agent skills
        data-agent metrics list --json
    """
    core = _get_agent()
    result = core.list_metrics()
    semantic_models = result.get("semantic_models") or {}
    
    # Flatten to simple list
    all_metrics: list[dict[str, str]] = []
    for model_name, measures in semantic_models.items():
        for m in measures:
            all_metrics.append({
                "name": m.get("name", ""),
                "description": m.get("description", ""),
            })
    
    if json_out:
        typer.echo(json.dumps({"metrics": all_metrics}, default=str))
        return
    
    if not all_metrics:
        typer.echo("No metrics found.")
        return
    
    typer.echo("Available metrics:")
    typer.echo("")
    for m in all_metrics:
        desc = f" — {m['description']}" if m['description'] else ""
        typer.echo(f"  • {m['name']}{desc}")
    typer.echo("")
    typer.echo(f"Total: {len(all_metrics)} metrics")


@metrics_app.command("describe")
def metrics_describe(
    name: str = typer.Argument(..., help="Metric name."),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output JSON for agent skills / scripting.",
    ),
) -> None:
    """Describe a metric (dimensions, time grains).
    
    Examples:
        data-agent metrics describe revenue
        data-agent metrics describe revenue --json
    """
    from falk.tools.semantic import get_semantic_model_info
    
    core = _get_agent()
    info = get_semantic_model_info(
        core.bsl_models,
        name,
        core.model_descriptions,
    )
    
    if not info:
        typer.echo(f"❌ Metric '{name}' not found.", err=True)
        raise typer.Exit(code=1)
    
    if json_out:
        payload = {
            "name": name,
            "description": info.description,
            "dimensions": [
                {
                    "name": d.name,
                    "description": d.description,
                    "type": d.type,
                }
                for d in info.dimensions
            ],
            "time_grains": info.time_grains,
        }
        typer.echo(json.dumps(payload, default=str))
        return
    
    # Human output
    typer.echo(f"*{name}*")
    if info.description:
        typer.echo("")
        typer.echo(info.description)
    typer.echo("")
    if info.dimensions:
        typer.echo("Can group by:")
        for d in info.dimensions[:10]:
            t = f" [{d.type}]" if d.type else ""
            desc = f" — {d.description}" if d.description else ""
            typer.echo(f"  • {d.name}{t}{desc}")
        if len(info.dimensions) > 10:
            typer.echo(f"  ... and {len(info.dimensions) - 10} more")
    typer.echo("")
    if info.time_grains:
        typer.echo("Time grains: " + ", ".join(info.time_grains))


# ---------------------------------------------------------------------------
# Metadata: dimensions
# ---------------------------------------------------------------------------


dimensions_app = typer.Typer(help="Explore available dimensions")
app.add_typer(dimensions_app, name="dimensions")


@dimensions_app.command("list")
def dimensions_list(
    domain: Optional[str] = typer.Option(
        None,
        "--domain",
        help="Filter by data domain (e.g. affiliate, finance, core).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output JSON for agent skills / scripting.",
    ),
) -> None:
    """List all available dimensions.
    
    Examples:
        # All dimensions
        data-agent dimensions list
        
        # Only affiliate dimensions
        data-agent dimensions list --domain affiliate
        
        # JSON output
        data-agent dimensions list --json
    """
    core = _get_agent()
    all_dims: list[dict[str, Any]] = []
    
    for model_name, model in core.bsl_models.items():
        for dim_name, dim in model.get_dimensions().items():
            desc = core.dimension_descriptions.get((model_name, dim_name), "") or ""
            dom = core.dimension_domains.get((model_name, dim_name), "") or ""
            if domain and dom.lower() != domain.lower():
                continue
            all_dims.append({
                "name": dim_name,
                "description": desc,
                "domain": dom,
                "type": "time" if getattr(dim, "is_time_dimension", False) else "categorical",
            })
    
    if json_out:
        typer.echo(json.dumps({"dimensions": all_dims}, default=str))
        return
    
    if not all_dims:
        typer.echo("No dimensions found.")
        return
    
    typer.echo("Available dimensions:")
    typer.echo("")
    for d in all_dims[:50]:
        parts = [f"  • {d['name']}"]
        if d["domain"]:
            parts.append(f"[{d['domain']}]")
        if d["description"]:
            parts.append(f"— {d['description']}")
        typer.echo(" ".join(parts))
    if len(all_dims) > 50:
        typer.echo(f"  ... and {len(all_dims) - 50} more")
    typer.echo("")
    typer.echo(f"Total: {len(all_dims)} dimensions")


@dimensions_app.command("describe")
def dimensions_describe(
    dimension_name: str = typer.Argument(..., help="Dimension name."),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output JSON for agent skills / scripting.",
    ),
) -> None:
    """Describe a dimension (type, description, domain).
    
    Examples:
        data-agent dimensions describe region
        data-agent dimensions describe region --json
    """
    core = _get_agent()
    
    found: dict[str, Any] | None = None
    for model_name, model in core.bsl_models.items():
        for dim_name, dim in model.get_dimensions().items():
            if dim_name == dimension_name:
                desc = core.dimension_descriptions.get((model_name, dim_name), "") or ""
                dom = core.dimension_domains.get((model_name, dim_name), "") or ""
                dim_type = "time" if getattr(dim, "is_time_dimension", False) else "categorical"
                found = {
                    "name": dim_name,
                    "description": desc,
                    "domain": dom,
                    "type": dim_type,
                }
                break
        if found:
            break
    
    if not found:
        typer.echo(f"❌ Dimension '{dimension_name}' not found.", err=True)
        raise typer.Exit(code=1)
    
    if json_out:
        typer.echo(json.dumps(found, default=str))
        return
    
    # Human output
    typer.echo(f"*{found['name']}*")
    typer.echo(f"Type: {found['type']}")
    if found["domain"]:
        typer.echo(f"Domain: {found['domain']}")
    if found["description"]:
        typer.echo("")
        typer.echo(found["description"])


# ---------------------------------------------------------------------------
# Config inspection
# ---------------------------------------------------------------------------


@app.command()
def config(
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output JSON for agent skills / scripting.",
    ),
) -> None:
    """Show loaded configuration (metrics count, dimensions count, paths).
    
    Useful for debugging what config is active.
    
    Examples:
        data-agent config
        data-agent config --json
    """
    core = _get_agent()
    
    # Count metrics
    result = core.list_metrics()
    semantic_models = result.get("semantic_models") or {}
    metric_count = sum(len(measures) for measures in semantic_models.values())
    
    # Count dimensions (unique by name)
    all_dim_names = set()
    for model in core.bsl_models.values():
        all_dim_names.update(model.get_dimensions().keys())
    dim_count = len(all_dim_names)
    
    # Paths
    settings = core._settings
    
    payload = {
        "metrics_count": metric_count,
        "dimensions_count": dim_count,
        "bsl_config_path": str(settings.bsl_models_path),
        "connection": settings.connection,
        "project_config_path": str(settings.project_root / "falk_project.yaml"),
    }
    
    if json_out:
        typer.echo(json.dumps(payload, default=str))
        return
    
    # Human output
    typer.echo("*falk Configuration*")
    typer.echo("")
    typer.echo(f"Metrics: {metric_count}")
    typer.echo(f"Dimensions: {dim_count}")
    typer.echo("")
    typer.echo("Paths:")
    typer.echo(f"  • Semantic models: {payload['bsl_config_path']}")
    typer.echo(f"  • Connection: {payload.get('connection', {}).get('type', '?')}")
    typer.echo(f"  • Project config: {payload['project_config_path']}")


# ---------------------------------------------------------------------------
# Evals
# ---------------------------------------------------------------------------


@app.command()
def evals(
    path: str = typer.Argument(
        default="evals",
        help="Path to YAML file or directory (default: evals/)",
    ),
    tag: Optional[list[str]] = typer.Option(
        None,
        "--tag",
        "-t",
        help="Only run cases matching these tags (repeatable).",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output for each case.",
    ),
) -> None:
    """Run YAML-based evaluation test cases.
    
    Examples:
        # Run all evals
        data-agent evals
        
        # Run evals from specific file
        data-agent evals examples/evals/basic.yaml
        
        # Run only synonym tests
        data-agent evals --tag synonyms
        
        # Verbose output
        data-agent evals -v
    """
    p = Path(path)
    if p.is_file():
        cases = load_cases(p)
    elif p.is_dir():
        cases = discover_cases(p)
    else:
        typer.echo(f"❌ Path not found: {p}", err=True)
        raise typer.Exit(code=1)
    
    if not cases:
        typer.echo(f"No eval cases found in {p}", err=True)
        raise typer.Exit(code=1)

    try:
        summary = run_evals(cases, verbose=verbose, tags=tag)
    except Exception as e:
        from falk.evals.runner import _sanitize_error

        typer.echo(_sanitize_error(str(e)), err=True)
        raise typer.Exit(code=1)

    if summary.failed or summary.errors:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Servers
# ---------------------------------------------------------------------------


@app.command()
def chat(
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Port to serve web UI on",
    ),
    reload: bool = typer.Option(
        True,
        "--reload/--no-reload",
        help="Auto-reload on code changes",
    ),
) -> None:
    """Start the web chat UI.
    
    Opens conversational web interface at http://localhost:8000
    
    Example:
        falk chat
        falk chat --port 3000
        falk chat --no-reload  # Production mode
    """
    import subprocess

    from falk.settings import load_settings

    settings = load_settings()
    cwd = str(settings.project_root)

    typer.echo(f"🌐 Starting web chat UI on http://localhost:{port}")
    typer.echo("   Press Ctrl+C to stop")
    typer.echo("")

    cmd = ["uvicorn", "falk.web:app", "--port", str(port), "--host", "0.0.0.0"]
    if reload:
        cmd.append("--reload")

    try:
        subprocess.run(cmd, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to start web UI: {e}", err=True)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        typer.echo("\n✅ Web UI stopped")


@app.command()
def slack() -> None:
    """Start the Slack bot server.
    
    Requires environment variables:
    - SLACK_BOT_TOKEN
    - SLACK_SIGNING_SECRET
    
    Example:
        falk slack
    """
    import subprocess
    import os
    
    # Check required env vars
    if not os.getenv("SLACK_BOT_TOKEN"):
        typer.echo("❌ SLACK_BOT_TOKEN not set in environment", err=True)
        typer.echo("   Add it to your .env file or export it", err=True)
        raise typer.Exit(code=1)
    
    if not os.getenv("SLACK_SIGNING_SECRET"):
        typer.echo("❌ SLACK_SIGNING_SECRET not set in environment", err=True)
        typer.echo("   Add it to your .env file or export it", err=True)
        raise typer.Exit(code=1)
    
    typer.echo("💬 Starting Slack bot server...")
    typer.echo("   Press Ctrl+C to stop")
    typer.echo("")
    
    try:
        subprocess.run(["python", "app/slack.py"], check=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to start Slack bot: {e}", err=True)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        typer.echo("\n✅ Slack bot stopped")


if __name__ == "__main__":
    app()

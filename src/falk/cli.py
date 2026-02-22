"""falk CLI - Project management, configuration, and servers.

This CLI focuses on project setup and management:
- Initialize and sync projects
- Run evaluations
- Start servers (MCP, chat, slack)
- Show configuration

For data queries and agent interactions, use:
- MCP server: `falk mcp` (connect from Cursor, Claude Desktop)
- Web chat: `falk chat` (Pydantic AI built-in web UI)
- Slack bot: `falk slack` (team collaboration)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import typer

from falk.evals.cases import load_cases
from falk.evals.runner import run_evals

app = typer.Typer(help="falk CLI - Manage projects, run evals, start servers")


def _print_section(title: str) -> None:
    typer.echo(f"\n=== {title} ===")


def _print_status(status: str, message: str, *, err: bool = False) -> None:
    typer.echo(f"[{status}] {message}", err=err)


# ---------------------------------------------------------------------------
# Project Management
# ---------------------------------------------------------------------------


def _copy_scaffold(src: Path, dst: Path) -> None:
    """Copy a single scaffold file."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)


def _copy_scaffold_dir(src_dir: Path, dst_dir: Path) -> None:
    """Recursively copy scaffold directory contents."""
    for item in src_dir.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(src_dir)
            _copy_scaffold(item, dst_dir / rel_path)


@app.command()
def init(
    project_name: str = typer.Argument(
        ...,
        help="Project name, or '.' to scaffold into the current directory",
    ),
    warehouse: str = typer.Option(
        "duckdb",
        "--warehouse",
        "-w",
        help="Warehouse type (duckdb, snowflake, bigquery, postgres)",
    ),
    sample_data: bool = typer.Option(
        True,
        "--sample-data/--no-sample-data",
        help="Include sample data (DuckDB only)",
    ),
) -> None:
    """Initialize a new falk project.
    
    Creates a new directory with:
    - falk_project.yaml (configuration)
    - semantic_models.yaml (metrics definitions)
    - RULES.md (agent behavior rules)
    - knowledge/ (business context)
    - .env.example (environment variables template)
    - Optional sample data (DuckDB)
    
    Example:
        falk init my-project
        falk init .                    # scaffold into current directory
        falk init analytics --warehouse snowflake --no-sample-data
    """
    # Import here to avoid circular dependency
    import importlib.resources
    
    init_in_place = project_name.strip() == "."
    if init_in_place:
        project_dir = Path.cwd().resolve()
        display_name = project_dir.name
        typer.echo(f"Initializing falk project in current directory: {project_dir}\n")
    else:
        project_dir = (Path.cwd() / project_name).resolve()
        display_name = project_name
        if project_dir.exists():
            typer.echo(f"[FAIL] Directory already exists: {project_dir}", err=True)
            raise typer.Exit(code=1)
        project_dir.mkdir(parents=True)
        typer.echo(f"[OK] Created project directory: {project_dir}")
    
    # Copy scaffold files
    try:
        # Get scaffold path using importlib.resources (Python 3.11+)
        scaffold_path = importlib.resources.files("falk").joinpath("scaffold")  # type: ignore
        
        # Core files
        _copy_scaffold(scaffold_path / "falk_project.yaml", project_dir / "falk_project.yaml")
        _copy_scaffold(scaffold_path / "semantic_models.yaml", project_dir / "semantic_models.yaml")
        _copy_scaffold(scaffold_path / "RULES.md", project_dir / "RULES.md")
        _copy_scaffold(scaffold_path / ".env.example", project_dir / ".env.example")
        
        # Knowledge directory (business context and gotchas)
        knowledge_src = scaffold_path / "knowledge"
        if knowledge_src.exists():
            _copy_scaffold_dir(knowledge_src, project_dir / "knowledge")
        
        # Evals directory (test cases)
        evals_src = scaffold_path / "evals"
        if evals_src.exists():
            _copy_scaffold_dir(evals_src, project_dir / "evals")

        # Project tools (demo extension)
        project_tools_src = scaffold_path / "project_tools"
        if project_tools_src.exists():
            _copy_scaffold_dir(project_tools_src, project_dir / "project_tools")
        
        typer.echo("[OK] Copied configuration files")
        
        # Update project name in falk_project.yaml
        config_path = project_dir / "falk_project.yaml"
        config_text = config_path.read_text(encoding="utf-8")
        config_text = config_text.replace("name: my-falk-project", f"name: {display_name}")
        config_path.write_text(config_text, encoding="utf-8")
        
        # Sample data (DuckDB only) - generate using seed script
        if warehouse == "duckdb" and sample_data:
            typer.echo("Generating sample data...")
            try:
                # Import and use the seed_data function
                from importlib.resources import files
                import sys
                import importlib.util
                
                # Load seed_data.py from scaffold
                seed_script = scaffold_path / "seed_data.py"
                spec = importlib.util.spec_from_file_location("seed_data", seed_script)
                if spec and spec.loader:
                    seed_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(seed_module)
                    
                    # Create database with sample data
                    db_path = project_dir / "data" / "warehouse.duckdb"
                    seed_module.create_example_database(db_path)
                    typer.echo("[OK] Generated sample data (DuckDB)")
            except Exception as e:
                typer.echo(f"[WARN] Could not generate sample data: {e}", err=True)
                typer.echo("      You can create it later by running the seed script")
        
        # Update warehouse config in falk_project.yaml if not duckdb
        if warehouse != "duckdb":
            config_path = project_dir / "falk_project.yaml"
            config_text = config_path.read_text()
            # This is a simple replacement - for production you'd want to parse YAML properly
            config_text = config_text.replace('type: duckdb', f'type: {warehouse}')
            config_path.write_text(config_text)
            typer.echo(f"[OK] Configured for {warehouse} warehouse")
        
        typer.echo(f"\n[PASS] Project initialized: {project_dir}")
        typer.echo("\nNext steps:")
        step = 1
        if not init_in_place:
            typer.echo(f"{step}. cd {project_name}")
            step += 1
        typer.echo(f"{step}. cp .env.example .env")
        step += 1
        typer.echo(f"{step}. Edit .env: set POSTGRES_URL and your LLM API key")
        step += 1
        typer.echo(f"{step}. falk validate --fast  # Validate configuration")
        step += 1
        typer.echo(f"{step}. falk mcp  # Start MCP server for queries")
        typer.echo("   OR falk chat  # Start local web UI")
        typer.echo("   Optional: uv run logfire auth && uv run logfire projects use <project-name>  # Enable observability")

    except Exception as e:
        typer.echo(f"\n[FAIL] Failed to initialize project: {e}", err=True)
        # Clean up on failure only if we created a new directory (not init .)
        if not init_in_place and project_dir.exists():
            shutil.rmtree(project_dir)
        raise typer.Exit(code=1)


@app.command()
def config(
    show_all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Show all configuration (including defaults)",
    ),
) -> None:
    """Show current falk configuration.
    
    Displays:
    - Project root
    - Semantic models path
    - Connection settings
    - Agent provider/model
    - LangFuse settings
    - Slack settings
    
    Example:
        falk config
        falk config --all
    """
    from falk.settings import load_settings
    
    try:
        settings = load_settings()
        
        typer.echo("falk Configuration\n")
        typer.echo(f"Project root: {settings.project_root}")
        typer.echo(f"Semantic models: {settings.bsl_models_path}")
        typer.echo("")
        
        # Connection
        conn = settings.connection
        typer.echo("[Connection]")
        typer.echo(f"  Type: {conn.get('type', '?')}")
        typer.echo(f"  Database: {conn.get('database', conn.get('project_id', '—'))}")
        typer.echo("")
        
        # Agent
        typer.echo("[Agent]")
        typer.echo(f"  Provider: {settings.agent.provider}")
        typer.echo(f"  Model: {settings.agent.model}")
        if show_all:
            typer.echo(f"  Auto-run: {settings.advanced.auto_run}")
            typer.echo(f"  Examples: {len(settings.agent.examples)}")
            typer.echo(f"  Rules: {len(settings.agent.rules)}")
        typer.echo("")
        
        # Session
        typer.echo("[Session]")
        typer.echo(f"  Store: {settings.session.store}")
        if settings.session.store == "postgres":
            typer.echo(f"  Postgres URL: {'Set' if settings.session.postgres_url else 'Not set (set POSTGRES_URL)'}")
        typer.echo("")

        # Observability (Logfire)
        logfire_configured = (
            bool(os.getenv("LOGFIRE_TOKEN") or os.getenv("LOGTAIL_TOKEN"))
            or (settings.project_root / ".logfire").exists()
        )
        typer.echo("[Observability]")
        typer.echo(
            f"  Logfire: {'Configured' if logfire_configured else 'Not configured (run: uv run logfire auth && uv run logfire projects use <name>)'}"
        )
        typer.echo("")
        
        # Slack
        typer.echo("[Slack]")
        typer.echo(f"  Bot token: {'Set' if settings.slack_bot_token else 'Not set'}")
        typer.echo(f"  App token: {'Set' if settings.slack_app_token else 'Not set'}")
        
    except Exception as e:
        typer.echo(f"[FAIL] Failed to load configuration: {e}", err=True)
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Testing & Validation
# ---------------------------------------------------------------------------


@app.command()
def validate(
    fast: bool = typer.Option(
        False,
        "--fast",
        "-f",
        help="Skip connection and agent initialization checks",
    ),
    no_connection: bool = typer.Option(
        False,
        "--no-connection",
        help="Skip warehouse connection test",
    ),
    no_agent: bool = typer.Option(
        False,
        "--no-agent",
        help="Skip agent initialization test",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed validation output",
    ),
) -> None:
    """Validate project configuration, semantic models, connection, and agent startup."""
    from falk.settings import load_settings
    from falk.validation import validate_project

    try:
        settings = load_settings()
        _print_section("Validate")
        _print_status("INFO", f"Project root: {settings.project_root}")

        check_connection = not no_connection and not fast
        check_agent = not no_agent and not fast
        summary = validate_project(
            project_root=settings.project_root,
            check_connection=check_connection,
            check_agent=check_agent,
        )

        for result in summary.results:
            if result.passed:
                _print_status("PASS", f"{result.check_name}: {result.message}")
            elif result.warning:
                _print_status("WARN", f"{result.check_name}: {result.message}")
            else:
                _print_status("FAIL", f"{result.check_name}: {result.message}")

            if verbose and result.details:
                for detail in result.details:
                    typer.echo(f"  - {detail}")

        _print_section("Summary")
        _print_status(
            "INFO",
            f"Checks: {len(summary.passed_checks)} passed, {len(summary.failed_checks)} failed, {len(summary.warnings)} warnings",
        )
        if not summary.passed:
            raise typer.Exit(code=1)
        _print_status("PASS", "Validation completed successfully.")
    except typer.Exit:
        raise
    except Exception as e:
        _print_status("FAIL", f"Validation failed: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def test(
    pattern: str = typer.Option(
        "*.yaml",
        "--pattern",
        "-p",
        help="Glob pattern for eval files in evals/",
    ),
    tags: str = typer.Option(
        "",
        "--tags",
        help="Comma-separated tags to filter eval cases (e.g. access,gotchas)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed eval output",
    ),
) -> None:
    """Run behavior evals from evals/ directory."""
    from falk.settings import load_settings

    try:
        settings = load_settings()
        project_root = settings.project_root
        evals_dir = project_root / "evals"

        _print_section("Test")
        _print_status("INFO", f"Project root: {project_root}")
        if not evals_dir.exists():
            _print_status("FAIL", f"Evals directory not found: {evals_dir}", err=True)
            _print_status("INFO", "Create evals/ directory with YAML files.", err=True)
            raise typer.Exit(code=1)

        case_files = sorted(evals_dir.glob(pattern))
        if not case_files:
            _print_status("FAIL", f"No eval files matched pattern '{pattern}' in {evals_dir}", err=True)
            raise typer.Exit(code=1)

        cases = []
        for file in case_files:
            cases.extend(load_cases(file))
        if not cases:
            _print_status("FAIL", f"No eval cases found in files matching '{pattern}'", err=True)
            raise typer.Exit(code=1)

        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        _print_status("INFO", f"Eval files: {len(case_files)}")
        _print_status("INFO", f"Cases loaded: {len(cases)}")
        if tag_list:
            _print_status("INFO", f"Tag filter: {', '.join(tag_list)}")

        summary = run_evals(cases, verbose=verbose, tags=tag_list or None)

        _print_section("Summary")
        _print_status("INFO", f"Pass rate: {summary.pass_rate:.1f}%")
        _print_status("INFO", f"Duration: {summary.duration_s:.1f}s")
        if summary.errors:
            _print_status("WARN", f"Errors: {summary.errors}")
        if summary.failed or summary.errors:
            _print_status("FAIL", "Eval suite failed.")
            raise typer.Exit(code=1)
        _print_status("PASS", "All eval cases passed.")
    except typer.Exit:
        raise
    except Exception as e:
        _print_status("FAIL", f"Eval run failed: {e}", err=True)
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Servers
# ---------------------------------------------------------------------------


@app.command("access-test")
def access_test(
    list_users: bool = typer.Option(
        False,
        "--list-users",
        help="Show configured user IDs from access_policies",
    ),
    user_id: str = typer.Option(
        None,
        "--user",
        "-u",
        help="User ID (e.g. email) to run as",
    ),
    question: str = typer.Option(
        "What metrics are available?",
        "--question",
        "-q",
        help="Question to ask the agent",
    ),
) -> None:
    """Run the agent as a specific user to test access policies.

    Requires access_policies in falk_project.yaml. Use --user to simulate
    different users (e.g. analyst@company.com, viewer@company.com).
    Use --list-users to see configured user IDs.

    Example:
        falk access-test --user analyst@company.com
        falk access-test --user viewer@company.com -q "Describe the orders metric"
        falk access-test --list-users
    """
    from falk.access import allowed_dimensions, allowed_metrics
    from falk.agent import DataAgent
    from falk.llm import build_agent
    from falk.settings import load_settings

    settings = load_settings()  # Load .env from project root

    if list_users:
        users = settings.access.users
        _print_section("Access Users")
        if not users:
            _print_status("WARN", "No users configured in access_policies.")
            _print_status("INFO", "Uncomment and configure access_policies in falk_project.yaml")
            return
        if settings.access.default_role:
            _print_status("INFO", f"Default role: {settings.access.default_role}")
        _print_status("INFO", "Configured users:")
        for u in users:
            typer.echo(f"  - {u.user_id}  roles: {u.roles}")
        return

    if not user_id:
        _print_status("FAIL", "--user is required (or use --list-users)", err=True)
        raise typer.Exit(code=1)

    allowed_m = allowed_metrics(user_id, settings.access)
    allowed_d = allowed_dimensions(user_id, settings.access)
    _print_section("Access Test")
    _print_status("INFO", f"User: {user_id}")
    _print_status("INFO", f"Question: {question}")
    if allowed_m is None:
        _print_status("INFO", "Allowed metrics: all")
    else:
        _print_status("INFO", f"Allowed metrics: {len(allowed_m)}")
    if allowed_d is None:
        _print_status("INFO", "Allowed dimensions: all")
    else:
        _print_status("INFO", f"Allowed dimensions: {len(allowed_d)}")

    try:
        agent = build_agent()
        deps = DataAgent()
        result = agent.run_sync(question, deps=deps, metadata={"user_id": user_id})
        output = result.output if hasattr(result, "output") else str(result)
        _print_section("Response")
        typer.echo(output or "No response")
    except Exception as e:
        _print_status("FAIL", f"access-test failed: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def mcp() -> None:
    """Start the MCP (Model Context Protocol) server.
    
    The MCP server exposes falk's data agent tools so any MCP client
    (Cursor, Claude Desktop, other Pydantic AI agents) can query governed metrics.
    
    The server uses stdio transport for compatibility with standard MCP clients.
    
    Example:
        falk mcp
    
    To connect from Cursor, add to your MCP config:
        {
          "mcpServers": {
            "falk": {
              "command": "falk",
              "args": ["mcp"],
              "cwd": "/path/to/your/falk-project"
            }
          }
        }
    """
    from falk.settings import load_settings
    load_settings()  # Load .env from project root
    
    typer.echo("Starting falk MCP server...", err=True)
    typer.echo("   Press Ctrl+C to stop", err=True)
    typer.echo("", err=True)
    
    try:
        from app.mcp import run_server
        run_server()
    except KeyboardInterrupt:
        typer.echo("\n[OK] MCP server stopped", err=True)
    except Exception as e:
        typer.echo(f"[FAIL] Failed to start MCP server: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def chat() -> None:
    """Start local web chat with the data agent (Pydantic AI built-in UI).

    Launches the FastAPI + Pydantic AI web app at http://127.0.0.1:8000.

    Example:
        falk chat
    """
    from falk.settings import load_settings

    load_settings()
    typer.echo("Starting falk chat (Pydantic AI web)...")
    typer.echo("   Open: http://127.0.0.1:8000")
    typer.echo("   Press Ctrl+C to stop")
    typer.echo("")

    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "app.web:app", "--host", "127.0.0.1", "--port", "8000"],
            check=True,
        )
    except KeyboardInterrupt:
        typer.echo("\n[OK] Chat server stopped")
    except Exception as e:
        typer.echo(f"[FAIL] Failed to start chat server: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def slack() -> None:
    """Start the Slack bot server.
    
    Requires environment variables:
    - SLACK_BOT_TOKEN
    - SLACK_APP_TOKEN
    
    The Slack bot connects to the MCP server internally.
    
    Example:
        falk slack
    """
    import subprocess
    import os
    
    from falk.settings import load_settings
    load_settings()  # Load .env from project root
    
    # Check required env vars
    if not os.getenv("SLACK_BOT_TOKEN"):
        typer.echo("[FAIL] SLACK_BOT_TOKEN not set in environment", err=True)
        typer.echo("   Add it to your .env file or export it", err=True)
        raise typer.Exit(code=1)
    
    if not os.getenv("SLACK_APP_TOKEN"):
        typer.echo("[FAIL] SLACK_APP_TOKEN not set in environment", err=True)
        typer.echo("   Add it to your .env file or export it", err=True)
        raise typer.Exit(code=1)
    
    typer.echo("Starting Slack bot server...")
    typer.echo("   Press Ctrl+C to stop")
    typer.echo("")
    
    try:
        subprocess.run([sys.executable, "-m", "app.slack"], check=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"[FAIL] Failed to start Slack bot: {e}", err=True)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        typer.echo("\n[OK] Slack bot stopped")


if __name__ == "__main__":
    app()

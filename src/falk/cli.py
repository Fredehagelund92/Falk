"""falk CLI - Project management, configuration, and servers.

This CLI focuses on project setup and management:
- Initialize and sync projects
- Run evaluations
- Start servers (MCP, chat, slack)
- Show configuration

For data queries and agent interactions, use:
- MCP server: `falk mcp` (connect from Cursor, Claude Desktop)
- Web UI: `falk chat` (conversational interface)
- Slack bot: `falk slack` (team collaboration)
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import typer

from falk.evals.cases import discover_cases, load_cases
from falk.evals.runner import run_evals

app = typer.Typer(help="falk CLI - Manage projects, run evals, start servers")


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
        typer.echo(f"{step}. Edit .env with your API keys")
        step += 1
        typer.echo(f"{step}. falk test --fast  # Validate configuration")
        step += 1
        typer.echo(f"{step}. falk mcp  # Start MCP server for queries")
        typer.echo("   OR falk chat  # Start web UI")
        
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
        
        typer.echo("📋 falk Configuration\n")
        typer.echo(f"Project root: {settings.project_root}")
        typer.echo(f"Semantic models: {settings.bsl_models_path}")
        typer.echo(f"Profile: {settings.profile or 'default'}")
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
        
        # LangFuse
        typer.echo("[LangFuse]")
        typer.echo(f"  Enabled: {settings.langfuse.enabled}")
        if settings.langfuse.enabled or show_all:
            typer.echo(f"  Host: {settings.langfuse.host}")
            typer.echo(f"  Project: {settings.langfuse.project_name}")
        typer.echo("")
        
        # Slack
        typer.echo("[Slack]")
        typer.echo(f"  Enabled: {settings.slack.enabled}")
        if settings.slack.enabled or show_all:
            typer.echo(f"  Bot token: {'Set' if settings.slack.bot_token else 'Not set'}")
            typer.echo(f"  App token: {'Set' if settings.slack.app_token else 'Not set'}")
        
    except Exception as e:
        typer.echo(f"[FAIL] Failed to load configuration: {e}", err=True)
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Testing & Validation
# ---------------------------------------------------------------------------


@app.command()
def test(
    fast: bool = typer.Option(
        False,
        "--fast",
        "-f",
        help="Skip connection test and evals (config validation only)",
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
    evals_only: bool = typer.Option(
        False,
        "--evals-only",
        help="Skip validation, only run evals",
    ),
    pattern: str = typer.Option(
        "*.yaml",
        "--pattern",
        "-p",
        help="Glob pattern for eval files",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed results",
    ),
) -> None:
    """Test project configuration, semantic models, and agent behavior.
    
    Runs comprehensive validation:
    1. Configuration validation (falk_project.yaml)
    2. Semantic layer validation (BSL models)
    3. Warehouse connection test (optional)
    4. Agent initialization test (optional)
    5. Evaluation test cases (if evals/ directory exists)
    
    Example:
        falk test                    # Full test suite
        falk test --fast             # Quick validation only
        falk test --no-connection    # Skip connection test
        falk test --evals-only       # Only run evals
        falk test --verbose          # Detailed output
    """
    from falk.settings import load_settings
    from falk.validation import validate_project
    
    try:
        settings = load_settings()
        project_root = settings.project_root
        
        # Skip validation if evals-only mode
        if not evals_only:
            typer.echo("Validating project...\n")
            
            # Run validation with appropriate flags
            check_connection = not no_connection and not fast
            check_agent = not no_agent and not fast
            
            validation = validate_project(
                project_root=project_root,
                check_connection=check_connection,
                check_agent=check_agent,
            )
            
            # Print validation results
            for result in validation.results:
                if result.passed:
                    typer.echo(f"[PASS] {result.check_name}: {result.message}")
                elif result.warning:
                    typer.echo(f"[WARN] {result.check_name}: {result.message}")
                else:
                    typer.echo(f"[FAIL] {result.check_name}: {result.message}")
                
                if verbose and result.details:
                    for detail in result.details:
                        typer.echo(f"       {detail}")
            
            typer.echo("")
            
            # Show summary
            passed_checks = len(validation.passed_checks)
            failed_checks = len(validation.failed_checks)
            warnings = len(validation.warnings)
            total = len(validation.results)
            
            if not validation.passed:
                typer.echo(f"[FAIL] Validation failed: {passed_checks}/{total} checks passed, {failed_checks} failed")
                if warnings > 0:
                    typer.echo(f"[WARN] {warnings} warning(s)")
                raise typer.Exit(code=1)
            
            typer.echo(f"[PASS] Validation passed: {passed_checks}/{total} checks")
            if warnings > 0:
                typer.echo(f"[WARN] {warnings} warning(s)")
            typer.echo("")
            
            # Exit early if fast mode
            if fast:
                typer.echo("[OK] Fast validation complete (skipped connection test and evals)")
                return
        
        # Run evaluations (if evals directory exists)
        evals_dir = project_root / "evals"
        
        if not evals_dir.exists():
            if evals_only:
                typer.echo(f"[FAIL] Evals directory not found: {evals_dir}", err=True)
                typer.echo("       Create evals/ directory with YAML files", err=True)
                raise typer.Exit(code=1)
            else:
                typer.echo("[INFO] No evals directory found (optional)")
                typer.echo("       Create evals/ directory with test cases to enable behavior testing")
                return
        
        typer.echo(f"Running evaluations from {evals_dir}\n")
        
        # Discover and load eval cases
        cases = discover_cases(evals_dir)
        if not cases:
            if evals_only:
                typer.echo(f"[FAIL] No eval cases found in {evals_dir}", err=True)
                raise typer.Exit(code=1)
            else:
                typer.echo(f"[INFO] No eval cases found in {evals_dir}")
                return
        
        typer.echo(f"Found {len(cases)} eval case(s)\n")
        
        # Run evaluations
        summary = run_evals(cases, verbose=verbose)
        
        # Print results
        typer.echo(f"\n[INFO] Eval Results: {summary.passed}/{summary.total} passed")
        if summary.errors > 0:
            typer.echo(f"[WARN] {summary.errors} error(s)")
        typer.echo(f"[INFO] Duration: {summary.duration_s:.1f}s")
        typer.echo(f"[OK] Pass rate: {summary.pass_rate:.1f}%")
        
        if verbose:
            typer.echo("\nDetailed Results:")
            for result in summary.results:
                status = "[PASS]" if result.passed else "[FAIL]"
                typer.echo(f"\n{status} {result.case.name}")
                if result.error:
                    typer.echo(f"       Error: {result.error}")
                elif result.failures:
                    typer.echo("       Failures:")
                    for failure in result.failures:
                        typer.echo(f"       - {failure}")
        
        # Exit with error if any tests failed
        if summary.failed > 0 or summary.errors > 0:
            typer.echo(f"\n[FAIL] Tests failed")
            raise typer.Exit(code=1)
        
        typer.echo(f"\n[PASS] All tests passed")
        
    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"\n[FAIL] Test failed: {e}", err=True)
        if verbose:
            import traceback
            typer.echo(traceback.format_exc(), err=True)
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Servers
# ---------------------------------------------------------------------------


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
    
    typer.echo("🔌 Starting falk MCP server...", err=True)
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
def chat(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-h",
        help="Host to bind to",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Port to bind to",
    ),
) -> None:
    """Start the web UI chat interface.
    
    Opens a browser-based chat interface for querying metrics.
    The web UI connects to the MCP server internally.
    
    Example:
        falk chat
        falk chat --port 8080
    """
    from falk.settings import load_settings
    load_settings()  # Load .env from project root
    
    typer.echo("💬 Starting falk web UI...")
    typer.echo(f"   URL: http://{host}:{port}")
    typer.echo("   Press Ctrl+C to stop")
    typer.echo("")
    
    try:
        # Import and run the web app
        from falk.llm import build_web_app
        import uvicorn
        
        app_instance = build_web_app()
        uvicorn.run(app_instance, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        typer.echo("\n[OK] Web UI stopped")


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
    
    typer.echo("💬 Starting Slack bot server...")
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

"""Example setup command for data-agent.

This module provides a CLI command to set up example configurations and seed data.
"""
from __future__ import annotations

import shutil
from pathlib import Path


def setup_example(
    config_dir: Path | None = None,
    data_dir: Path | None = None,
    overwrite: bool = False,
) -> None:
    """Set up example configurations and seed data.
    
    Args:
        config_dir: Directory for config files (default: config/).
        data_dir: Directory for data files (default: data/).
        overwrite: If True, overwrite existing files. If False, skip existing files.
    """
    if config_dir is None:
        config_dir = Path.cwd() / "config"
    if data_dir is None:
        data_dir = Path.cwd() / "data"
    
    # Ensure directories exist
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Find examples directory (could be in package or repo root)
    examples_dir = _find_examples_dir()
    if examples_dir is None:
        raise RuntimeError(
            "Could not find examples directory. "
            "Make sure you're running from the repository root or have the package installed."
        )
    
    # Copy config files
    config_examples = examples_dir / "config"
    if config_examples.exists():
        for config_file in config_examples.glob("*.yaml"):
            dest = config_dir / config_file.name
            if dest.exists() and not overwrite:
                print(f"⊘ Skipping {dest.name} (already exists, use --overwrite to replace)")
            else:
                shutil.copy2(config_file, dest)
                print(f"✓ Copied {config_file.name} to {config_dir}")
    
    # Seed database
    # Import seed_data directly from examples directory
    seed_data_path = examples_dir / "seed_data.py"
    if not seed_data_path.exists():
        print(f"⚠ Warning: Could not find seed_data.py in {examples_dir}")
        return
    
    # Execute seed_data as a module
    import importlib.util
    spec = importlib.util.spec_from_file_location("seed_data", seed_data_path)
    seed_data = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_data)
    create_example_database = seed_data.create_example_database
    
    db_path = data_dir / "warehouse.duckdb"
    if db_path.exists() and not overwrite:
        print(f"⊘ Skipping database creation (already exists, use --overwrite to replace)")
    else:
        create_example_database(db_path)
    
    print("\n✓ Example setup complete!")
    print(f"\nNext steps:")
    print(f"  1. Set your LLM API key in .env (see env.example)")
    print(f"  2. Run the agent: uv run uvicorn app.web:app --reload")
    print(f"\nTry asking:")
    print(f"  - 'What was our total revenue last month?'")
    print(f"  - 'Top 5 product categories by revenue'")


def _find_examples_dir() -> Path | None:
    """Find the examples directory, checking package location and repo root."""
    # Try package location first (if installed)
    try:
        import falk
        package_dir = Path(falk.__file__).parent.parent
        examples_dir = package_dir / "examples"
        if examples_dir.exists():
            return examples_dir
    except (ImportError, AttributeError):
        pass
    
    # Try repo root (for development)
    repo_root = Path.cwd()
    examples_dir = repo_root / "examples"
    if examples_dir.exists():
        return examples_dir
    
    return None


def main() -> None:
    """CLI entry point for example setup."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Set up example configurations and seed data for data-agent"
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory for config files (default: config/)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Directory for data files (default: data/)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files",
    )
    
    args = parser.parse_args()
    
    try:
        setup_example(
            config_dir=args.config_dir,
            data_dir=args.data_dir,
            overwrite=args.overwrite,
        )
    except Exception as e:
        print(f"✗ Error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()


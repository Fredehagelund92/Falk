"""CLI entry point: ``uv run python -m falk.evals``."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from falk.evals.cases import discover_cases, load_cases
from falk.evals.runner import run_evals


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run data-agent evaluation suite",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="evals",
        help="Path to a YAML file or directory of eval cases (default: evals/)",
    )
    parser.add_argument(
        "--tags",
        nargs="*",
        help="Only run cases matching these tags",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output for each case",
    )
    args = parser.parse_args()

    p = Path(args.path)
    if p.is_file():
        cases = load_cases(p)
    elif p.is_dir():
        cases = discover_cases(p)
    else:
        print(f"Path not found: {p}")
        print("Create eval cases in evals/ — see examples/evals/ for the format.")
        sys.exit(1)

    if not cases:
        print(f"No eval cases found in {p}")
        print("Create eval cases in evals/ — see examples/evals/ for the format.")
        sys.exit(1)

    print(f"Found {len(cases)} eval case(s) from {p}")

    summary = run_evals(cases, verbose=args.verbose, tags=args.tags)

    sys.exit(0 if summary.failed == 0 and summary.errors == 0 else 1)


if __name__ == "__main__":
    main()



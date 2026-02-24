"""Evaluation framework for the data agent.

Run test cases against the agent and measure quality. Catches regressions,
validates prompt changes, and ensures synonym/gotcha configs work correctly.

Quick start::

    uv run python -m falk.evals            # run all test cases
    uv run python -m falk.evals --verbose   # see detailed output

Test cases are defined in YAML files (see ``examples/evals/``).
"""

from falk.evals.cases import EvalCase, load_cases
from falk.evals.runner import run_evals

__all__ = ["EvalCase", "load_cases", "run_evals"]

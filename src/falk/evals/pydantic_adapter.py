"""Adapters to use Pydantic Evals with the falk eval cases.

This module does **not** depend on Pydantic Evals' concrete Python API so that
it remains stable across library versions. Instead, it converts our YAML-based
``EvalCase`` objects into plain Python dicts that match the conceptual
``Dataset`` → ``Case`` → ``metadata`` structure described in the
`pydantic-evals` documentation.

You can then feed the returned dataset into Pydantic Evals from your own
experiment script or notebook.

Example usage (inside your own Pydantic Evals script)::

    from falk.evals.cases import load_cases
    from falk.evals.pydantic_adapter import to_pydantic_evals_dataset

    cases = load_cases(\"evals/basic.yaml\")
    dataset = to_pydantic_evals_dataset(cases, name=\"data-agent-basic\")

    # PSEUDO-CODE – consult Pydantic Evals docs for the exact API:
    #
    # from pydantic_evals import Dataset, Case, EqualsExpected, run
    #
    # pe_dataset = Dataset(
    #     name=dataset[\"name\"],
    #     cases=[Case(**c) for c in dataset[\"cases\"]],
    # )
    #
    # results = run(
    #     dataset=pe_dataset,
    #     task=your_agent_callable,
    #     evaluators=[EqualsExpected(field=\"expected_contains\", ...)],
    # )
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from falk.evals.cases import EvalCase


def _case_to_record(case: EvalCase) -> dict[str, Any]:
    """Convert an ``EvalCase`` into a generic record for Pydantic Evals.

    The structure intentionally mirrors the high-level concepts in the
    Pydantic Evals docs:

    - ``input``: the user question
    - ``expected``: a loose, structured expectation description
    - ``metadata``: everything else (tags, tool expectations, etc.)
    """
    # Represent our expectations in a structured way that a custom
    # Pydantic Evals evaluator can understand.
    expected: dict[str, Any] = {
        "expect_tool": list(case.expect_tool),
        "expect_contains": list(case.expect_contains),
        "expect_not_contains": list(case.expect_not_contains),
        "expect_metric": case.expect_metric,
        "expect_group_by": case.expect_group_by,
        "expect_filters": case.expect_filters,
        "max_tool_calls": case.max_tool_calls,
    }

    # Metadata is kept fairly rich so you can slice/dice in your experiments.
    metadata: dict[str, Any] = {
        "name": case.name,
        "tags": list(case.tags),
        # Also embed the raw dataclass for advanced usage if desired.
        "raw_case": asdict(case),
    }

    return {
        "input": case.question,
        "expected": expected,
        "metadata": metadata,
    }


def to_pydantic_evals_dataset(
    cases: Iterable[EvalCase],
    *,
    name: str = "data-agent-evals",
) -> dict[str, Any]:
    """Convert ``EvalCase`` objects into a generic Pydantic Evals dataset dict.

    The returned structure is intentionally minimal and version-agnostic:

    .. code-block:: python

        {
            \"name\": \"data-agent-evals\",
            \"cases\": [
                {
                    \"input\": \"What was our revenue last month?\",
                    \"expected\": {...},
                    \"metadata\": {...},
                },
                ...
            ],
        }

    You can adapt this into concrete Pydantic Evals ``Dataset`` / ``Case``
    objects using whatever API version you're on.
    """
    return {
        "name": name,
        "cases": [_case_to_record(c) for c in cases],
    }




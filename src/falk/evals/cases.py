"""Test case definitions for agent evaluation.

Each ``EvalCase`` represents a single question + expected behavior. Cases are
loaded from YAML files so non-engineers can contribute them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class EvalCase:
    """A single evaluation test case.

    Attributes:
        name: Human-readable test name (used in reports).
        question: The user question to send to the agent.
        expect_tool: Tool(s) the agent MUST call (e.g. ``"query_metric"``).
        expect_contains: Substrings the response MUST contain (case-insensitive).
        expect_not_contains: Substrings the response must NOT contain.
        expect_metric: If set, ``query_metric`` must be called with this metric.
        expect_group_by: If set, ``query_metric`` must group by this dimension.
        expect_filters: If set, ``query_metric`` must include a filter on this dim.
        allow_tool_skip_if_contains: If response contains all of these (case-insensitive),
            tool/metric/group_by/filters checks are skipped. Use for gotcha cases where
            the agent may explain the caveat instead of querying.
        allow_no_tool: If True, passing with 0 tool calls is allowed (e.g. out-of-scope
            questions where the agent should say "This request is outside my capabilities").
        tags: Optional tags for filtering (e.g. ``["synonyms", "gotchas"]``).
        max_tool_calls: Max number of tool calls allowed (catches infinite loops).
    """

    name: str
    question: str
    expect_tool: list[str] = field(default_factory=list)
    expect_contains: list[str] = field(default_factory=list)
    expect_not_contains: list[str] = field(default_factory=list)
    expect_metric: str | None = None
    expect_group_by: str | None = None
    expect_filters: str | None = None
    allow_tool_skip_if_contains: list[str] = field(default_factory=list)
    allow_no_tool: bool = False
    tags: list[str] = field(default_factory=list)
    max_tool_calls: int = 8


def load_cases(path: str | Path) -> list[EvalCase]:
    """Load test cases from a YAML file.

    YAML format (either)::

        # Top-level list
        - question: "What was our total revenue?"
          expect_tool: [query_metric]
          expect_metric: revenue

        # Or with cases key
        cases:
          - question: "What was our total revenue?"
            expect_tool: [query_metric]

    Args:
        path: Path to a YAML file.

    Returns:
        List of ``EvalCase`` objects.
    """
    def _to_list(x: Any) -> list:
        if not x:
            return []
        return [x] if isinstance(x, str) else list(x)

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, list):
        cases_raw = raw
    elif isinstance(raw, dict):
        cases_raw = raw.get("cases") or []
    else:
        cases_raw = []
    out: list[EvalCase] = []

    for item in cases_raw:
        if not isinstance(item, dict):
            continue
        # Support both expect_* and expected_* field names
        def get(key: str, *alt_keys: str) -> Any:
            for k in (key,) + alt_keys:
                v = item.get(k)
                if v is not None:
                    return v
            return None

        # Normalize expect_tool to list
        et = get("expect_tool", "expected_tool") or []
        if isinstance(et, str):
            et = [et]
        # Normalize expect_contains / expect_not_contains to list
        ec = get("expect_contains", "expected_contains", "expected_mentions") or []
        if isinstance(ec, str):
            ec = [ec]
        enc = get("expect_not_contains", "expected_not_contains") or []
        if isinstance(enc, str):
            enc = [enc]
        tags = get("tags") or []
        if isinstance(tags, str):
            tags = [tags]

        # expect_group_by can be list or str
        egb = get("expect_group_by", "expected_group_by")
        if isinstance(egb, list) and egb:
            egb = egb[0] if len(egb) == 1 else str(egb)
        egb = str(egb) if egb else None

        out.append(EvalCase(
            name=get("name") or "unnamed",
            question=get("question") or "",
            expect_tool=et,
            expect_contains=ec,
            expect_not_contains=enc,
            expect_metric=get("expect_metric", "expected_metric"),
            expect_group_by=egb,
            expect_filters=get("expect_filters", "expected_filters"),
            allow_tool_skip_if_contains=_to_list(get("allow_tool_skip_if_contains")),
            allow_no_tool=bool(get("allow_no_tool")),
            tags=tags,
            max_tool_calls=get("max_tool_calls") or 8,
        ))

    return out


def discover_cases(directory: str | Path = "evals") -> list[EvalCase]:
    """Discover and load all YAML eval cases from a directory.

    Scans ``directory`` (default: ``evals/``) for ``*.yaml`` / ``*.yml`` files
    and loads all cases from them.
    """
    d = Path(directory)
    if not d.exists():
        return []

    all_cases: list[EvalCase] = []
    for f in sorted(d.glob("*.yaml")) + sorted(d.glob("*.yml")):
        all_cases.extend(load_cases(f))
    return all_cases



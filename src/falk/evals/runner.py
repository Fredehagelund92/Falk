"""Evaluation runner — executes test cases against the agent and reports results.

Usage::

    from falk.evals import run_evals, load_cases

    cases = load_cases("evals/basic.yaml")
    results = run_evals(cases, verbose=True)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from falk.agent import DataAgent
from falk.evals.cases import EvalCase

logger = logging.getLogger(__name__)


def _sanitize_error(err: str) -> str:
    """Convert raw API errors to user-friendly messages."""
    lower = err.lower()
    if "not set" in lower and "api_key" in lower:
        return err  # Already a clear message from our pre-check
    if "invalid_api_key" in lower or "incorrect api key" in lower or "401" in err:
        return "Invalid API key. Check OPENAI_API_KEY in .env at https://platform.openai.com/account/api-keys"
    if "invalid_request_error" in lower and "api_key" in lower:
        return "Invalid API key. Check OPENAI_API_KEY in .env"
    if "rate_limit" in lower or "429" in err:
        return "Rate limit exceeded. Wait a moment and try again."
    if "insufficient_quota" in lower:
        return "API quota exceeded. Check your OpenAI billing at https://platform.openai.com/account/billing"
    if "anthropic" in lower and ("invalid" in lower or "401" in err):
        return "Invalid API key. Check ANTHROPIC_API_KEY in .env"
    # Avoid exposing API keys or long JSON
    if "sk-" in err or "api_key" in lower:
        return "API authentication failed. Check your API key in .env"
    if len(err) > 200:
        return err[:197] + "..."
    return err


@dataclass
class EvalResult:
    """Result of running a single evaluation case."""

    case: EvalCase
    passed: bool
    response: str = ""
    tool_calls: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    duration_s: float = 0.0
    error: str | None = None
    tool_call_details: list[tuple[str, dict]] = field(default_factory=list)


@dataclass
class EvalSummary:
    """Aggregate results from an evaluation run."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    results: list[EvalResult] = field(default_factory=list)
    duration_s: float = 0.0

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total else 0.0


def run_evals(
    cases: list[EvalCase],
    *,
    verbose: bool = False,
    tags: list[str] | None = None,
) -> EvalSummary:
    """Run evaluation cases against the agent.

    Args:
        cases: List of ``EvalCase`` to run.
        verbose: Print detailed output for each case.
        tags: If set, only run cases matching at least one tag.

    Returns:
        ``EvalSummary`` with aggregated results.
    """
    import os

    from falk import build_agent
    from falk.settings import load_settings

    # Fail fast with clear message if API key missing
    s = load_settings()
    provider = (s.agent.provider or "openai").lower()
    if provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY not set. Add it to .env or export it."
        )
    if provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Add it to .env or export it."
        )
    if provider in ("google", "google-genai") and not os.environ.get("GOOGLE_API_KEY"):
        raise RuntimeError(
            "GOOGLE_API_KEY not set. Add it to .env or export it."
        )

    # Filter by tags if specified
    if tags:
        tag_set = set(tags)
        cases = [c for c in cases if tag_set & set(c.tags)]

    if not cases:
        logger.warning("No eval cases to run.")
        return EvalSummary()

    agent = build_agent()
    deps = DataAgent()
    summary = EvalSummary(total=len(cases))
    run_start = time.monotonic()

    for i, case in enumerate(cases, 1):
        if verbose:
            print(f"\n{'='*60}")
            print(f"[{i}/{len(cases)}] {case.name}")
            print(f"  Q: {case.question}")
        else:
            print(f"[{i}/{len(cases)}] {case.question[:50]}{'...' if len(case.question) > 50 else ''}", end=" ", flush=True)

        result = _run_single(agent, case, deps)

        if not verbose:
            print("PASS" if result.passed else ("ERROR" if result.error else "FAIL"))
        summary.results.append(result)

        if result.error:
            summary.errors += 1
            if verbose:
                print(f"  ERROR: {result.error}")
        elif result.passed:
            summary.passed += 1
            if verbose:
                print(f"  PASS ({result.duration_s:.1f}s, {len(result.tool_calls)} tool calls)")
        else:
            summary.failed += 1
            if verbose:
                print(f"  FAIL ({result.duration_s:.1f}s)")
                for f in result.failures:
                    print(f"    - {f}")
                if result.tool_calls:
                    print(f"    (saw tools: {result.tool_calls})")
                if result.tool_call_details:
                    for name, args in result.tool_call_details:
                        print(f"    {name}({args})")

    summary.duration_s = time.monotonic() - run_start

    # Print summary
    if verbose:
        print()
    status = f"{summary.passed}/{summary.total} passed"
    if summary.failed or summary.errors:
        status += f" ({summary.failed} failed"
        if summary.errors:
            status += f", {summary.errors} error(s)"
        status += ")"
    print(f"{status} in {summary.duration_s:.1f}s")
    if summary.failed:
        for r in summary.results:
            if not r.passed and not r.error:
                print(f"  FAIL: {r.case.name}")
                for f in r.failures:
                    print(f"    - {f}")
    if summary.errors:
        for r in summary.results:
            if r.error:
                print(f"  ERROR: {r.case.name} — {r.error}")

    return summary


def _run_single(agent: Any, case: EvalCase, deps: DataAgent) -> EvalResult:
    """Run a single eval case and check assertions."""
    start = time.monotonic()
    result = EvalResult(case=case, passed=False)

    try:
        run_result = agent.run_sync(case.question, deps=deps)
        elapsed = time.monotonic() - start
        result.duration_s = elapsed

        # Extract response text
        response_text = ""
        if hasattr(run_result, "output"):
            response_text = str(run_result.output or "")
        elif hasattr(run_result, "data"):
            response_text = str(run_result.data or "")
        result.response = response_text

        # Extract tool calls from message history
        tool_calls = _extract_tool_calls(run_result)
        result.tool_calls = tool_calls
        result.tool_call_details = list(_iter_tool_call_parts(run_result))

        # --- Assertions ---
        failures: list[str] = []
        response_lower = response_text.lower()

        # If allow_tool_skip_if_contains: when response has all these, skip tool checks
        skip_tool_checks = bool(
            case.allow_tool_skip_if_contains
            and all(n.lower() in response_lower for n in case.allow_tool_skip_if_contains)
        )

        # Check expected tools were called (unless skip_tool_checks)
        if not skip_tool_checks:
            for expected_tool in case.expect_tool:
                if expected_tool not in tool_calls:
                    failures.append(
                        f"Expected tool '{expected_tool}' to be called, "
                        f"but only saw: {tool_calls or ['(none)']}"
                    )

        # Agent must call a tool unless it correctly says "outside my capabilities" or case allows no tool
        if not tool_calls and not skip_tool_checks and not case.allow_no_tool:
            outside_ok = "outside my capabilities" in response_lower
            if not outside_ok:
                failures.append(
                    "Agent must call a tool to answer (or respond 'This request is outside my capabilities'). Saw 0 tool calls."
                )

        # Check response contains expected substrings
        for needle in case.expect_contains:
            if needle.lower() not in response_lower:
                failures.append(
                    f"Expected response to contain '{needle}'"
                )

        # Check response does NOT contain forbidden substrings
        for needle in case.expect_not_contains:
            if needle.lower() in response_lower:
                failures.append(
                    f"Expected response NOT to contain '{needle}'"
                )

        # Check max tool calls (catch infinite loops)
        if len(tool_calls) > case.max_tool_calls:
            failures.append(
                f"Too many tool calls: {len(tool_calls)} > max {case.max_tool_calls}"
            )

        # Check metric/group_by/filters in tool calls (unless skip_tool_checks)
        if not skip_tool_checks:
            if case.expect_metric:
                if not _tool_arg_matches(run_result, "query_metric", "metrics", case.expect_metric):
                    failures.append(
                        f"Expected query_metric to use metric '{case.expect_metric}' (in metrics list)"
                    )
            if case.expect_group_by:
                if not _tool_arg_contains(run_result, "query_metric", "group_by", case.expect_group_by):
                    failures.append(
                        f"Expected query_metric to include group_by='{case.expect_group_by}'"
                    )
            if case.expect_filters:
                if not _tool_arg_contains(run_result, "query_metric", "filters", case.expect_filters):
                    failures.append(
                        f"Expected query_metric to filter on '{case.expect_filters}'"
                    )

        result.failures = failures
        result.passed = len(failures) == 0

    except Exception as e:
        result.error = _sanitize_error(str(e))
        result.passed = False
        result.duration_s = time.monotonic() - start

    return result


def _extract_tool_calls(run_result: Any) -> list[str]:
    """Extract tool names from a PydanticAI run result's message history."""
    tool_names: list[str] = []
    get_msgs = getattr(run_result, "all_messages", None) or getattr(run_result, "new_messages", None)
    if get_msgs and callable(get_msgs):
        messages = get_msgs()
        for msg in messages:
            if hasattr(msg, "parts"):
                for part in msg.parts:
                    if hasattr(part, "tool_name") and part.tool_name:
                        tool_names.append(part.tool_name)
    # Fallback: extract from run_result.response (last ModelResponse)
    if not tool_names and hasattr(run_result, "response"):
        resp = run_result.response
        if hasattr(resp, "parts"):
            for part in resp.parts:
                if hasattr(part, "tool_name") and part.tool_name:
                    tool_names.append(part.tool_name)
    return tool_names


def _get_tool_args(part: Any) -> dict[str, Any]:
    """Get tool call args as dict, handling JSON string or dict.
    Prefer args_as_dict() for ToolCallPart/BuiltinToolCallPart (handles both formats).
    """
    if hasattr(part, "args_as_dict") and callable(getattr(part, "args_as_dict")):
        try:
            return part.args_as_dict() or {}
        except Exception:
            pass
    args = getattr(part, "args", None) or {}
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            import json

            return json.loads(args) or {}
        except Exception:
            return {}
    return {}


def _iter_tool_call_parts(run_result: Any):
    """Yield (tool_name, args) from parts that have tool_name and args (ToolCallPart, BuiltinToolCallPart)."""
    get_msgs = getattr(run_result, "all_messages", None) or getattr(run_result, "new_messages", None)
    messages = get_msgs() if get_msgs and callable(get_msgs) else []
    for msg in messages:
        if not hasattr(msg, "parts"):
            continue
        for part in msg.parts:
            if not hasattr(part, "tool_name") or not part.tool_name:
                continue
            if not hasattr(part, "args") and not hasattr(part, "args_as_dict"):
                continue
            yield part.tool_name, _get_tool_args(part)
    if not messages and hasattr(run_result, "response"):
        resp = run_result.response
        if hasattr(resp, "parts"):
            for part in resp.parts:
                if hasattr(part, "tool_name") and part.tool_name and (
                    hasattr(part, "args") or hasattr(part, "args_as_dict")
                ):
                    yield part.tool_name, _get_tool_args(part)


def _tool_arg_matches(
    run_result: Any,
    tool_name: str,
    arg_name: str,
    expected_value: str,
) -> bool:
    """Check if a tool call used a specific argument value."""
    expected_lower = expected_value.lower()
    for name, args in _iter_tool_call_parts(run_result):
        if name != tool_name:
            continue
        val = args.get(arg_name)
        if val is None:
            continue
        if isinstance(val, str) and val.lower().strip() == expected_lower:
            return True
        if isinstance(val, list) and expected_lower in [str(v).lower().strip() for v in val]:
            return True
        if str(val).lower().strip() == expected_lower:
            return True
    return False


def _tool_arg_contains(
    run_result: Any,
    tool_name: str,
    arg_name: str,
    expected_substring: str,
) -> bool:
    """Check if a tool call's argument contains a substring (works for lists and dicts)."""
    needle = expected_substring.lower()
    for name, args in _iter_tool_call_parts(run_result):
        if name != tool_name:
            continue
        val = args.get(arg_name)
        if val is not None and needle in str(val).lower():
            return True
    return False



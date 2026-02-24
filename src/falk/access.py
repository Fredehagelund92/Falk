"""Access control — metric and dimension filtering per user.

All functions are pure (no I/O). Tools in falk.llm call these helpers before
returning data to the LLM.

Three-way return from allowed_*:
  None        → open access, return everything unchanged
  non-empty   → filter results to this set of names
  empty set   → user has roles, but none grant access to anything
"""

from __future__ import annotations

from falk.settings import AccessConfig


def _policy_is_open(cfg: AccessConfig) -> bool:
    """True when no access_policies section was configured at all."""
    return not cfg.roles and not cfg.users and cfg.default_role is None


def _roles_for_user(user_id: str | None, cfg: AccessConfig) -> list[str]:
    """Return effective roles for a user_id.

    Resolution:
    1. Explicit entry in cfg.users matched by user_id.
    2. cfg.default_role if set.
    3. Empty list → open access (no restriction).
    """
    if user_id:
        for mapping in cfg.users:
            if mapping.user_id == user_id:
                return list(mapping.roles)
    if cfg.default_role:
        return [cfg.default_role]
    return []


def allowed_metrics(user_id: str | None, cfg: AccessConfig) -> set[str] | None:
    """Return allowed metric names for this user.

    Returns None for open access (no filter needed).
    Returns empty set if user has roles but none grant any metric.
    """
    if _policy_is_open(cfg):
        return None

    roles = _roles_for_user(user_id, cfg)
    if not roles:
        return None  # no mapping + no default_role = open

    result: set[str] = set()
    for role_name in roles:
        policy = cfg.roles.get(role_name)
        if policy is None:
            continue  # unknown role name — skip silently
        if policy.metrics is None:
            return None  # this role grants all metrics
        result.update(policy.metrics)
    return result


def allowed_dimensions(user_id: str | None, cfg: AccessConfig) -> set[str] | None:
    """Return allowed dimension names for this user.

    Returns None for open access (no filter needed).
    Returns empty set if user has roles but none grant any dimension.
    """
    if _policy_is_open(cfg):
        return None

    roles = _roles_for_user(user_id, cfg)
    if not roles:
        return None

    result: set[str] = set()
    for role_name in roles:
        policy = cfg.roles.get(role_name)
        if policy is None:
            continue
        if policy.dimensions is None:
            return None  # this role grants all dimensions
        result.update(policy.dimensions)
    return result


def filter_metrics(metrics: list[dict], allowed: set[str] | None) -> list[dict]:
    """Filter a list of metric dicts to only allowed names.
    If allowed is None (open access), returns the list unchanged.
    """
    if allowed is None:
        return metrics
    return [m for m in metrics if m.get("name") in allowed]


def filter_dimensions(dimensions: list[dict], allowed: set[str] | None) -> list[dict]:
    """Filter a list of dimension dicts to only allowed names."""
    if allowed is None:
        return dimensions
    return [d for d in dimensions if d.get("name") in allowed]


def is_metric_allowed(name: str, allowed: set[str] | None) -> bool:
    """Check whether a single metric name is permitted."""
    return allowed is None or name in allowed


def is_dimension_allowed(name: str, allowed: set[str] | None) -> bool:
    """Check whether a single dimension name is permitted."""
    return allowed is None or name in allowed

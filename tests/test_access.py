"""Unit tests for falk.access — access control and metric/dimension filtering."""
from __future__ import annotations

import pytest

from falk.access import (
    allowed_dimensions,
    allowed_metrics,
    filter_dimensions,
    filter_metrics,
    is_dimension_allowed,
    is_metric_allowed,
)
from falk.settings import AccessConfig, RolePolicy, UserMapping


def test_open_access_when_no_policies():
    """Open access when AccessConfig is empty."""
    cfg = AccessConfig()
    assert allowed_metrics("alice@co.com", cfg) is None
    assert allowed_dimensions("alice@co.com", cfg) is None


def test_explicit_user_mapping():
    """User in users with role gets correct metric/dimension sets."""
    cfg = AccessConfig(
        roles={
            "analyst": RolePolicy(
                metrics=["revenue", "orders"],
                dimensions=["date", "region"],
            ),
        },
        users=[UserMapping(user_id="alice@co.com", roles=["analyst"])],
    )
    assert allowed_metrics("alice@co.com", cfg) == {"revenue", "orders"}
    assert allowed_dimensions("alice@co.com", cfg) == {"date", "region"}


def test_default_role_for_unlisted_user():
    """Unlisted user with default_role gets that role's permissions."""
    cfg = AccessConfig(
        roles={
            "viewer": RolePolicy(metrics=["revenue"], dimensions=["date"]),
        },
        default_role="viewer",
    )
    assert allowed_metrics("unknown@co.com", cfg) == {"revenue"}
    assert allowed_dimensions("unknown@co.com", cfg) == {"date"}


def test_role_with_metrics_null_grants_all():
    """Admin-style role with metrics: null grants all (returns None)."""
    cfg = AccessConfig(
        roles={
            "admin": RolePolicy(metrics=None, dimensions=None),
        },
        users=[UserMapping(user_id="admin@co.com", roles=["admin"])],
    )
    assert allowed_metrics("admin@co.com", cfg) is None
    assert allowed_dimensions("admin@co.com", cfg) is None


def test_empty_role_returns_empty_set():
    """Role with metrics: [] or dimensions: [] returns empty set."""
    cfg = AccessConfig(
        roles={
            "restricted": RolePolicy(metrics=[], dimensions=[]),
        },
        users=[UserMapping(user_id="restricted@co.com", roles=["restricted"])],
    )
    assert allowed_metrics("restricted@co.com", cfg) == set()
    assert allowed_dimensions("restricted@co.com", cfg) == set()


def test_multiple_roles_union():
    """User with multiple roles gets union of permissions."""
    cfg = AccessConfig(
        roles={
            "analyst": RolePolicy(metrics=["revenue", "orders"], dimensions=["date", "region"]),
            "viewer": RolePolicy(metrics=["revenue"], dimensions=["date"]),
        },
        users=[UserMapping(user_id="alice@co.com", roles=["analyst", "viewer"])],
    )
    assert allowed_metrics("alice@co.com", cfg) == {"revenue", "orders"}
    assert allowed_dimensions("alice@co.com", cfg) == {"date", "region"}


def test_filter_metrics():
    """filter_metrics filters to allowed set; None returns unchanged."""
    metrics = [{"name": "revenue"}, {"name": "orders"}, {"name": "clicks"}]
    assert filter_metrics(metrics, {"revenue", "clicks"}) == [
        {"name": "revenue"},
        {"name": "clicks"},
    ]
    assert filter_metrics(metrics, None) == metrics


def test_filter_dimensions():
    """filter_dimensions filters to allowed set; None returns unchanged."""
    dimensions = [{"name": "date"}, {"name": "region"}, {"name": "product"}]
    assert filter_dimensions(dimensions, {"date", "product"}) == [
        {"name": "date"},
        {"name": "product"},
    ]
    assert filter_dimensions(dimensions, None) == dimensions


def test_is_metric_allowed():
    """is_metric_allowed: None = all allowed; else check membership."""
    assert is_metric_allowed("revenue", None) is True
    assert is_metric_allowed("revenue", {"revenue", "orders"}) is True
    assert is_metric_allowed("clicks", {"revenue", "orders"}) is False
    assert is_metric_allowed("revenue", set()) is False


def test_is_dimension_allowed():
    """is_dimension_allowed: None = all allowed; else check membership."""
    assert is_dimension_allowed("date", None) is True
    assert is_dimension_allowed("date", {"date", "region"}) is True
    assert is_dimension_allowed("product", {"date", "region"}) is False
    assert is_dimension_allowed("date", set()) is False


def test_unlisted_user_no_default_role_open():
    """Unlisted user with no default_role gets open access."""
    cfg = AccessConfig(
        roles={"analyst": RolePolicy(metrics=["revenue"], dimensions=["date"])},
        users=[UserMapping(user_id="alice@co.com", roles=["analyst"])],
        default_role=None,
    )
    assert allowed_metrics("other@co.com", cfg) is None
    assert allowed_dimensions("other@co.com", cfg) is None


def test_user_id_none():
    """user_id=None with default_role gets default_role."""
    cfg = AccessConfig(
        roles={"viewer": RolePolicy(metrics=["revenue"], dimensions=["date"])},
        default_role="viewer",
    )
    assert allowed_metrics(None, cfg) == {"revenue"}
    assert allowed_dimensions(None, cfg) == {"date"}

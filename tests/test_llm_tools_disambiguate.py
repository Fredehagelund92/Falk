from __future__ import annotations

from falk.llm.tools import _matches_concept


def test_matches_concept_bidirectional_substring_for_total_revenue():
    item = {
        "name": "revenue",
        "display_name": "Revenue",
        "description": "Total revenue in USD",
        "synonyms": ["sales", "income", "turnover"],
    }

    assert _matches_concept(item, "total revenue")


def test_matches_concept_includes_description():
    item = {
        "name": "revenue",
        "display_name": "Revenue",
        "description": "Total revenue in USD",
        "synonyms": [],
    }

    assert _matches_concept(item, "revenue in usd")


def test_matches_concept_uses_token_subset_not_exact_phrase():
    item = {
        "name": "average_order_value",
        "display_name": "Average Order Value",
        "description": "Average revenue per order",
        "synonyms": ["aov", "avg order size", "basket size"],
    }

    assert _matches_concept(item, "order value")


def test_matches_concept_returns_false_for_unrelated_term():
    item = {
        "name": "revenue",
        "display_name": "Revenue",
        "description": "Total revenue in USD",
        "synonyms": ["sales", "income", "turnover"],
    }

    assert not _matches_concept(item, "margin")

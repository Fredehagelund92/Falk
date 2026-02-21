from __future__ import annotations

from datetime import date

from falk.tools.calculations import compute_deltas, compute_shares, suggest_date_range


def test_compute_shares():
    data = [{"region": "US", "revenue": 75}, {"region": "EU", "revenue": 25}]
    out = compute_shares(data, "revenue")
    assert out[0]["share_pct"] == 75.0
    assert out[1]["share_pct"] == 25.0


def test_compute_deltas():
    current = [{"region": "US", "revenue": 120}]
    previous = [{"region": "US", "revenue": 100}]
    out = compute_deltas(current, previous, "revenue", ["region"])
    assert out[0]["delta"] == 20.0
    assert out[0]["current"] == 120.0
    assert out[0]["previous"] == 100.0


def test_suggest_date_range_last_7_days():
    out = suggest_date_range("last_7_days", reference=date(2026, 2, 20))
    assert out == {"start": "2026-02-14", "end": "2026-02-20"}

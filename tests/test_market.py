import csv
from datetime import datetime, timezone

import pytest

from forex_demo.market import MarketSnapshot, MarketSnapshotError


def snapshot_row(*, server="FinexBisnisSolusi-Demo", account="demo", observed="2026-11-06T12:00:00Z"):
    row = ["1", observed, account, server, "EURUSD", "M5", "1.085", "1.0852", "2.0", "0.00001", "5", "5"]
    for minute in range(5):
        row.extend([f"2026.11.06 11:{55 + minute:02d}", "1.084", "1.086", "1.083", "1.085", "100"])
    return row


def write_snapshot(path, row):
    with path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerow(row)


def test_reads_atomic_bridge_snapshot_and_builds_model_context(tmp_path):
    path = tmp_path / "snapshot.csv"
    write_snapshot(path, snapshot_row())

    now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    snapshot = MarketSnapshot.read(path, now_utc=now)

    assert snapshot.symbol == "EURUSD"
    assert snapshot.timeframe == "M5"
    assert snapshot.spread_points == 2
    assert len(snapshot.bars) == 5
    assert snapshot.to_context(now_utc=now)["market_snapshot"]["candles"][-1]["close"] == 1.085


def test_rejects_wrong_demo_server_and_invalid_quotes(tmp_path):
    path = tmp_path / "snapshot.csv"
    write_snapshot(path, snapshot_row(server="wrong"))
    with pytest.raises(MarketSnapshotError, match="server"):
        MarketSnapshot.read(path, expected_server="FinexBisnisSolusi-Demo")

    row = snapshot_row()
    row[7] = "1.084"  # ask below bid
    write_snapshot(path, row)
    with pytest.raises(MarketSnapshotError, match="ask"):
        MarketSnapshot.read(path)


def test_rejects_stale_or_oversized_snapshot(tmp_path):
    path = tmp_path / "snapshot.csv"
    write_snapshot(path, snapshot_row(observed="2026-11-06T11:56:00Z"))
    with pytest.raises(MarketSnapshotError, match="stale"):
        MarketSnapshot.read(path, now_utc=datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc))

    path.write_bytes(b"x" * 10_000)
    with pytest.raises(MarketSnapshotError, match="size"):
        MarketSnapshot.read(path)

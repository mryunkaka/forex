"""Strict reader for the MT5 shadow bridge's atomic CSV snapshot."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class MarketSnapshotError(ValueError):
    """Raised when the quote file is absent, malformed, unsafe, or stale."""


@dataclass(frozen=True, slots=True)
class Candle:
    time_server: str
    open: float
    high: float
    low: float
    close: float
    tick_volume: int


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    observed_at_utc: datetime
    account_mode: str
    server: str
    symbol: str
    timeframe: str
    bid: float
    ask: float
    spread_points: float
    point: float
    digits: int
    bars: tuple[Candle, ...]

    @classmethod
    def read(
        cls,
        path: str | Path,
        *,
        expected_server: str | None = None,
        expected_symbol: str | None = None,
        now_utc: datetime | None = None,
        max_age: timedelta = timedelta(seconds=90),
    ) -> "MarketSnapshot":
        source = Path(path)
        try:
            if source.stat().st_size > 8192:
                raise MarketSnapshotError("snapshot size exceeds 8192 bytes")
            raw = source.read_text(encoding="utf-8-sig")
        except MarketSnapshotError:
            raise
        except OSError:
            raise MarketSnapshotError("snapshot is unavailable") from None
        if len(raw.encode("utf-8")) > 8192:
            raise MarketSnapshotError("snapshot size exceeds 8192 bytes")
        try:
            rows = list(csv.reader(raw.splitlines()))
        except csv.Error:
            raise MarketSnapshotError("snapshot is not valid CSV") from None
        if len(rows) != 1 or len(rows[0]) < 12:
            raise MarketSnapshotError("snapshot has an invalid row")
        row = rows[0]
        try:
            version = int(row[0])
            observed = cls._parse_utc(row[1])
            account_mode, server, symbol, timeframe = row[2:6]
            bid, ask, spread, point = (cls._finite_float(value) for value in row[6:10])
            digits, bar_count = int(row[10]), int(row[11])
        except (ValueError, IndexError):
            raise MarketSnapshotError("snapshot fields are malformed") from None
        if version != 1:
            raise MarketSnapshotError("snapshot version is unsupported")
        if account_mode != "demo":
            raise MarketSnapshotError("snapshot account is not demo")
        if expected_server and server != expected_server:
            raise MarketSnapshotError("snapshot server does not match the configured demo server")
        if expected_symbol and symbol != expected_symbol:
            raise MarketSnapshotError("snapshot symbol does not match configuration")
        if not server or not symbol or timeframe != "M5":
            raise MarketSnapshotError("snapshot identity or timeframe is invalid")
        if not 1 <= digits <= 8 or point <= 0:
            raise MarketSnapshotError("snapshot point or digits are invalid")
        if bid <= 0 or ask < bid or spread < 0:
            raise MarketSnapshotError("snapshot bid/ask/spread is invalid")
        if bar_count != 5 or len(row) != 12 + bar_count * 6:
            raise MarketSnapshotError("snapshot must contain exactly five completed candles")
        now = now_utc or datetime.now(timezone.utc)
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise MarketSnapshotError("clock must use UTC")
        age = now.astimezone(timezone.utc) - observed
        if age < timedelta(seconds=-15):
            raise MarketSnapshotError("snapshot timestamp is in the future")
        if age > max_age:
            raise MarketSnapshotError("snapshot is stale")

        bars: list[Candle] = []
        for offset in range(12, len(row), 6):
            time_server = row[offset].strip()
            try:
                opening, high, low, close = (cls._finite_float(value) for value in row[offset + 1:offset + 5])
                volume = int(row[offset + 5])
            except ValueError:
                raise MarketSnapshotError("snapshot candle is malformed") from None
            if not time_server or volume < 0 or high < max(opening, close) or low > min(opening, close) or low > high:
                raise MarketSnapshotError("snapshot candle OHLCV is invalid")
            bars.append(Candle(time_server, opening, high, low, close, volume))
        return cls(observed, account_mode, server, symbol, timeframe, bid, ask, spread, point, digits, tuple(bars))

    @staticmethod
    def _finite_float(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite number")
        return number

    @staticmethod
    def _parse_utc(value: str) -> datetime:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise ValueError("timestamp must use UTC")
        return parsed.astimezone(timezone.utc)

    def to_context(self, *, now_utc: datetime) -> dict[str, Any]:
        return {
            "current_time_utc": now_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "market_snapshot": {
                "observed_at_utc": self.observed_at_utc.isoformat().replace("+00:00", "Z"),
                "account_mode": self.account_mode,
                "server": self.server,
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "bid": self.bid,
                "ask": self.ask,
                "spread_points": self.spread_points,
                "digits": self.digits,
                "candles": [
                    {"time_server": bar.time_server, "open": bar.open, "high": bar.high,
                     "low": bar.low, "close": bar.close, "tick_volume": bar.tick_volume}
                    for bar in self.bars
                ],
            },
        }

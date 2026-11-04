"""Fail-closed loader for demo/shadow settings; secret values are not retained."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


class RuntimeConfigError(ValueError):
    """Raised when runtime configuration is incomplete or unsafe."""


_REQUIRED = {
    "APP_ENV",
    "TRADING_MODE",
    "TRADING_EXECUTION_ENABLED",
    "BROKER_NAME",
    "MT5_EXPECTED_ACCOUNT_MODE",
    "MT5_EXPECTED_SERVER",
    "MT5_SYMBOL",
    "MT5_TIMEFRAME",
    "MODEL_PROVIDER_ENABLED",
    "MODEL_BASE_URL",
    "MODEL_ID",
    "MODEL_DAILY_CALL_LIMIT",
}
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,31}$")
_SERVER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,127}$")


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    app_env: str
    trading_mode: str
    trading_execution_enabled: bool
    broker_name: str
    mt5_expected_account_mode: str
    mt5_expected_server: str
    mt5_symbol: str
    mt5_timeframe: str
    model_provider_enabled: bool
    model_base_url: str
    model_id: str
    model_daily_call_limit: int


def _boolean(values: Mapping[str, str], key: str) -> bool:
    raw = values[key].strip().lower()
    if raw not in {"true", "false"}:
        raise RuntimeConfigError(f"{key} must be true or false")
    return raw == "true"


def load_runtime_config(values: Mapping[str, str]) -> RuntimeConfig:
    missing = _REQUIRED - set(values)
    if missing:
        raise RuntimeConfigError("missing settings: " + ", ".join(sorted(missing)))

    # Fail closed even if someone edits .env: these gates cannot be enabled by config.
    if values["APP_ENV"].strip().lower() != "demo":
        raise RuntimeConfigError("APP_ENV must be demo")
    if values["TRADING_MODE"].strip().lower() != "shadow":
        raise RuntimeConfigError("TRADING_MODE must be shadow")
    execution_enabled = _boolean(values, "TRADING_EXECUTION_ENABLED")
    if execution_enabled:
        raise RuntimeConfigError("TRADING_EXECUTION_ENABLED must remain false")
    provider_enabled = _boolean(values, "MODEL_PROVIDER_ENABLED")
    if provider_enabled:
        raise RuntimeConfigError("MODEL_PROVIDER_ENABLED must remain false until provider limits are verified")

    broker = values["BROKER_NAME"].strip().upper()
    account_mode = values["MT5_EXPECTED_ACCOUNT_MODE"].strip().lower()
    server = values["MT5_EXPECTED_SERVER"].strip()
    symbol = values["MT5_SYMBOL"].strip().upper()
    timeframe = values["MT5_TIMEFRAME"].strip().upper()
    if broker != "FINEX":
        raise RuntimeConfigError("BROKER_NAME must be FINEX")
    if account_mode != "demo":
        raise RuntimeConfigError("MT5_EXPECTED_ACCOUNT_MODE must be demo")
    if not _SERVER_RE.fullmatch(server):
        raise RuntimeConfigError("MT5_EXPECTED_SERVER must be a confirmed non-empty server name")
    if not _SYMBOL_RE.fullmatch(symbol):
        raise RuntimeConfigError("MT5_SYMBOL must be a confirmed symbol code")
    if timeframe != "M5":
        raise RuntimeConfigError("MT5_TIMEFRAME must be M5")

    base_url = values["MODEL_BASE_URL"].strip()
    parsed_url = urlparse(base_url)
    if parsed_url.scheme != "https" or not parsed_url.hostname:
        raise RuntimeConfigError("MODEL_BASE_URL must be an HTTPS URL")
    model_id = values["MODEL_ID"].strip()
    if model_id != "cx/gpt-6-luna":
        raise RuntimeConfigError("MODEL_ID does not match the configured project model")
    try:
        daily_limit = int(values["MODEL_DAILY_CALL_LIMIT"])
    except (TypeError, ValueError) as exc:
        raise RuntimeConfigError("MODEL_DAILY_CALL_LIMIT must be an integer from 0 through 5") from exc
    if not 0 <= daily_limit <= 5:
        raise RuntimeConfigError("MODEL_DAILY_CALL_LIMIT must be an integer from 0 through 5")

    return RuntimeConfig(
        app_env="demo",
        trading_mode="shadow",
        trading_execution_enabled=False,
        broker_name=broker,
        mt5_expected_account_mode="demo",
        mt5_expected_server=server,
        mt5_symbol=symbol,
        mt5_timeframe="M5",
        model_provider_enabled=False,
        model_base_url=base_url,
        model_id=model_id,
        model_daily_call_limit=daily_limit,
    )


def load_runtime_config_file(path: str | Path) -> RuntimeConfig:
    """Read supported .env keys while ignoring secret and unrelated values."""
    values: dict[str, str] = {}
    supported = _REQUIRED
    for line_number, raw_line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise RuntimeConfigError(f"invalid .env line {line_number}")
        key, value = (part.strip() for part in line.split("=", 1))
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise RuntimeConfigError(f"invalid .env key on line {line_number}")
        if key not in supported:
            continue
        if key in values:
            raise RuntimeConfigError(f"duplicate .env setting {key}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return load_runtime_config(values)

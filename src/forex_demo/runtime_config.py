"""Fail-closed loader for demo/shadow settings; secret values are not retained."""

from __future__ import annotations

import ipaddress
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
    "MODEL_TIMEOUT_SECONDS",
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
    model_timeout_seconds: int
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

    # Fail closed even if someone edits .env: live mode and order execution
    # cannot be enabled by runtime configuration.
    if values["APP_ENV"].strip().lower() != "demo":
        raise RuntimeConfigError("APP_ENV must be demo")
    if values["TRADING_MODE"].strip().lower() != "shadow":
        raise RuntimeConfigError("TRADING_MODE must be shadow")
    execution_enabled = _boolean(values, "TRADING_EXECUTION_ENABLED")
    if execution_enabled:
        raise RuntimeConfigError("TRADING_EXECUTION_ENABLED must remain false")
    provider_enabled = _boolean(values, "MODEL_PROVIDER_ENABLED")
    if provider_enabled and not values.get("MODEL_API_KEY", "").strip():
        raise RuntimeConfigError("MODEL_API_KEY is required when MODEL_PROVIDER_ENABLED is true")

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
    hostname = parsed_url.hostname
    if not hostname or parsed_url.username is not None or parsed_url.password is not None:
        raise RuntimeConfigError("MODEL_BASE_URL must be an HTTPS URL or loopback HTTP URL")
    is_loopback = hostname.lower() == "localhost"
    try:
        is_loopback = is_loopback or ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        pass
    if parsed_url.scheme != "https" and not (parsed_url.scheme == "http" and is_loopback):
        raise RuntimeConfigError("MODEL_BASE_URL must be an HTTPS URL or loopback HTTP URL")
    model_id = values["MODEL_ID"].strip()
    if model_id != "cx/gpt-6-luna":
        raise RuntimeConfigError("MODEL_ID does not match the configured project model")
    try:
        timeout_seconds = int(values["MODEL_TIMEOUT_SECONDS"])
    except (TypeError, ValueError) as exc:
        raise RuntimeConfigError("MODEL_TIMEOUT_SECONDS must be an integer from 1 through 60") from exc
    if not 1 <= timeout_seconds <= 60:
        raise RuntimeConfigError("MODEL_TIMEOUT_SECONDS must be an integer from 1 through 60")
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
        model_provider_enabled=provider_enabled,
        model_base_url=base_url,
        model_id=model_id,
        model_timeout_seconds=timeout_seconds,
        model_daily_call_limit=daily_limit,
    )


def load_runtime_config_file(path: str | Path) -> RuntimeConfig:
    """Read supported .env keys while ignoring secret and unrelated values."""
    values: dict[str, str] = {}
    # Read the credential only to check presence; never include it in RuntimeConfig.
    supported = _REQUIRED | {"MODEL_API_KEY"}
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


def read_model_api_key(path: str | Path) -> str:
    """Read the request credential separately so config/log records never retain it."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        raise RuntimeConfigError("cannot read runtime environment file") from None
    found: str | None = None
    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key != "MODEL_API_KEY":
            continue
        if found is not None:
            raise RuntimeConfigError("duplicate MODEL_API_KEY setting")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if not value or "\n" in value or "\r" in value:
            raise RuntimeConfigError(f"invalid MODEL_API_KEY on line {line_number}")
        found = value
    return found or ""

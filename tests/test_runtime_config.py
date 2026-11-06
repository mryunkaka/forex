import pytest

from forex_demo.runtime_config import RuntimeConfigError, load_runtime_config, load_runtime_config_file, read_model_api_key


BASE = {
    "APP_ENV": "demo",
    "TRADING_MODE": "shadow",
    "TRADING_EXECUTION_ENABLED": "false",
    "BROKER_NAME": "FINEX",
    "MT5_EXPECTED_ACCOUNT_MODE": "demo",
    "MT5_EXPECTED_SERVER": "Finex-Demo-Server",
    "MT5_SYMBOL": "EURUSD",
    "MT5_TIMEFRAME": "M5",
    "MODEL_PROVIDER_ENABLED": "false",
    "MODEL_BASE_URL": "https://9router.example/v1",
    "MODEL_ID": "cx/gpt-6-luna",
    "MODEL_TIMEOUT_SECONDS": "10",
    "MODEL_DAILY_CALL_LIMIT": "5",
}


def test_loads_shadow_demo_settings_and_pair():
    config = load_runtime_config(BASE)

    assert config.broker_name == "FINEX"
    assert config.mt5_expected_server == "Finex-Demo-Server"
    assert config.mt5_symbol == "EURUSD"
    assert config.mt5_timeframe == "M5"
    assert config.trading_mode == "shadow"
    assert config.trading_execution_enabled is False
    assert config.model_provider_enabled is False


def test_allows_plain_http_only_for_loopback_model_endpoint():
    values = dict(BASE, MODEL_BASE_URL="http://127.0.0.1:20128/v1")

    config = load_runtime_config(values)

    assert config.model_base_url == "http://127.0.0.1:20128/v1"


def test_rejects_plain_http_model_endpoint_for_non_loopback_host():
    values = dict(BASE, MODEL_BASE_URL="http://9router.example/v1")

    with pytest.raises(RuntimeConfigError, match="loopback HTTP URL"):
        load_runtime_config(values)


def test_rejects_loopback_http_url_with_embedded_credentials():
    values = dict(BASE, MODEL_BASE_URL="http://user:secret@127.0.0.1:20128/v1")

    with pytest.raises(RuntimeConfigError, match="loopback HTTP URL"):
        load_runtime_config(values)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("APP_ENV", "live"),
        ("TRADING_MODE", "live"),
        ("TRADING_EXECUTION_ENABLED", "true"),
        ("MT5_EXPECTED_ACCOUNT_MODE", "real"),
    ],
)
def test_rejects_unsafe_modes_and_unverified_provider(key, value):
    values = dict(BASE, **{key: value})

    with pytest.raises(RuntimeConfigError):
        load_runtime_config(values)


def test_provider_can_be_enabled_in_demo_shadow_with_key_but_key_is_not_retained():
    values = dict(BASE, MODEL_PROVIDER_ENABLED="true", MODEL_API_KEY="test-secret")

    config = load_runtime_config(values)

    assert config.model_provider_enabled is True
    assert "test-secret" not in repr(config)


def test_provider_enabled_requires_api_key():
    values = dict(BASE, MODEL_PROVIDER_ENABLED="true")

    with pytest.raises(RuntimeConfigError, match="MODEL_API_KEY"):
        load_runtime_config(values)


@pytest.mark.parametrize("key", ["MT5_EXPECTED_SERVER", "MT5_SYMBOL"])
def test_requires_explicit_server_and_symbol(key):
    values = dict(BASE, **{key: ""})

    with pytest.raises(RuntimeConfigError, match=key):
        load_runtime_config(values)


def test_env_file_loader_reads_settings_without_logging_or_returning_secrets(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(f"{key}={value}" for key, value in BASE.items())
        + "\nMODEL_API_KEY=do-not-return-this-value\n",
        encoding="utf-8",
    )

    config = load_runtime_config_file(env_path)

    assert config.mt5_symbol == "EURUSD"
    assert "do-not-return-this-value" not in repr(config)


def test_rejects_duplicate_runtime_setting_in_env_file(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("MT5_SYMBOL=EURUSD\nMT5_SYMBOL=EURUSD.a\n", encoding="utf-8")

    with pytest.raises(RuntimeConfigError, match="duplicate"):
        load_runtime_config_file(env_path)


def test_reads_api_key_only_for_request_client_and_rejects_duplicate(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("MODEL_API_KEY='private-value'\n", encoding="utf-8")
    assert read_model_api_key(env_path) == "private-value"
    env_path.write_text("MODEL_API_KEY=one\nMODEL_API_KEY=two\n", encoding="utf-8")
    with pytest.raises(RuntimeConfigError, match="duplicate"):
        read_model_api_key(env_path)

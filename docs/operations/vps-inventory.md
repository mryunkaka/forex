# VPS inventory and current setup

Date checked: 2026-11-04 UTC. This note excludes public IPs, account identifiers, and credentials.

## Host

- Ubuntu 24.04.5 LTS, x86_64, Azure kernel.
- 4 vCPU, 54 GiB RAM, no swap.
- Root volume: 61 GiB total, approximately 27 GiB free at inventory time.
- systemd is running. No active desktop session or GUI display manager was present.
- No firewall settings were changed. SSH is key-only for `saidadam28`; a root-owned backup of the SSH configuration is at `/var/backups/ssh-pre-key-only-20261104T092741Z.tar.gz`.

## Installed for a private MT5 desktop

- WineHQ staging 11.21 is installed from the signed WineHQ Noble repository, with Wine 32-bit support. This replaces Ubuntu Wine 9's `wine` package; a pre-change package manifest is at `/var/backups/packages-pre-wine-staging-20261104T095856Z.txt`. Installing it added Wine dependencies. The old Wine 9 prefix remains untouched.
- Xvfb, x11vnc, noVNC, and websockify are installed from Ubuntu packages.
- The original MetaQuotes MT5 installation remains in `~/.mt5-finex-demo`. A second MT5 installation was created in `~/.mt5-finex-demo-staging-11.21` for the Wine 11.21 compatibility attempt; the former prefix was not deleted or modified.
- Wine prefix `~/.mt5` was created before 32-bit Wine support and later failed `kernel32.dll` initialization. It was left untouched for diagnosis/recovery; the new prefix is separate.
- The Microsoft WebView2 installer did not finish within its timeout. Do not assume WebView2 is installed.
- `mt5-demo-ui.service` is active but disabled at boot. It runs MT5 under Wine 11.21 staging in the separate prefix, on Xvfb display `:77`; x11vnc listens on `127.0.0.1:5900`, and noVNC/websockify listens on `127.0.0.1:6080`. Service/launcher backups from before this change are under `/var/backups/mt5-demo-ui*.pre-wine11-20261104T100032Z`.
- The Windows-side SSH tunnel is bound only to `127.0.0.1:16080`. No firewall port was opened. The local noVNC page returned HTTP 200.

## Project checkout and configuration

- Project cloned to the VPS home directory from the public `main` branch at commit `7f772c2`.
- EA31337 submodule is pinned at `9b9bd38c4e49dd6916f4fe3936e50e97fca7a692`; recursive submodule clone completed.
- A VPS-local `.env` with permissions `0600` sets FINEX demo, server `FinexBisnisSolusi-Demo`, symbol `EURUSD`, M5, shadow mode, model disabled, and order execution disabled. It contains no API key or MT5 password.
- Runtime configuration validation passed against that `.env`.

## Acceptance status

- SSH public-key authentication works with strict host-key checking. A fresh session was tested with client password auth disabled; server policy now requires `publickey` for `saidadam28`. Effective `sshd -T` confirms password and keyboard-interactive auth are disabled for this account. The underlying account password has not been reset.
- Wine 11.21 staging MT5 terminal is running, and the loopback noVNC page returns HTTP 200 through the local SSH tunnel. The Wine 9 debugger alert triggered a migration to a separate prefix. User confirmed the active MT5 server is `FinexBisnisSolusi-Demo`.
- The previously exposed SSH password and 9Router API key were not used. User rotated the 9Router key and entered the replacement directly into the VPS `.env`; the key value is not recorded here.
- The user has logged into the current Wine 11.21 terminal, and confirmed the demo server `FinexBisnisSolusi-Demo`. Do not send the trading password through chat.
- MetaEditor command-line compilation of pinned EA31337 failed with 100 errors and 60 warnings on the current MT5 build. No EA31337 `.ex5` was produced, installed, or attached. The unmodified EA is not safe to attach because it bypasses the project's planned shadow/risk adapter.
- The remote project `.env` has `MODEL_PROVIDER_ENABLED=false` and `TRADING_EXECUTION_ENABLED=false`; the rotated 9Router key is present but not printed. No 9Router client or Python service entry point is implemented or running, so no 9Router completion request, news polling, or trade occurred.
- User confirmed the active MT5 account server is `FinexBisnisSolusi-Demo`.
- The VPS-local 9Router endpoint at `127.0.0.1:20128/v1/models` returned HTTP 200 and includes `cx/gpt-6-luna`. The configured public URL returned HTTP 403 from the VPS. A local-only SSH tunnel to the 9Router dashboard is available at `http://127.0.0.1:12128/dashboard/endpoint` and redirects to its login page. No model completion request has been sent; enforceable call/cost caps remain unverified.
- No service is enabled at boot. Review the incomplete Wine/WebView2/EA compilation state before considering persistent operation.

## Follow-up check (2026-11-05)

- The user entered the rotated `MODEL_API_KEY` directly into the VPS `.env`; only presence was checked, and the value was never printed or copied into source control.
- `MODEL_PROVIDER_ENABLED=false` and `TRADING_EXECUTION_ENABLED=false` remain in force. MT5 UI is active; no Forex bot service is installed/running and no `EA31337.ex5` exists in the active MT5 prefix.
- Authenticated GET `/v1/models` to the configured public URL `https://9router.saijaan.my.id/v1` returned HTTP 403. The loopback service `http://127.0.0.1:20128/v1/models` returned HTTP 200 and lists `cx/gpt-6-luna`, both with and without Authorization; this only verifies model listing, not that the configured key is accepted or that chat completions work.
- Read-only inspection of the local 9Router SQLite metadata found an active API-key entry and usage history. The `apiKeys` table has no per-key budget or rate-limit fields, and no monthly spend or daily-call cap was found in settings. Do not assume a hard cost cap exists; no completion has been sent.
- At this check, the endpoint was not yet configured for loopback. Remaining blockers were enforceable spending/call limits and an implemented/validated shadow runtime. EA compilation/integration remains a separate blocker. No trading or model request occurred.
- Rechecked after the user reported the endpoint fix: the configured public `/v1/models` endpoint still returned HTTP 403 from the VPS. The replacement key remains present, but this response does not verify successful authentication. Provider and trading execution remain disabled; no model completion or trade was sent.
- SSH diagnostic response identifies Cloudflare Error 1010, `browser_signature_banned`, with `Server: cloudflare`. The request is blocked at Cloudflare based on client/browser signature, so it does not establish whether the 9Router API key is valid. No model completion or trade was sent.
- The user-provided `http://127.0.0.1:12128/v1` works from the Windows workstation through the SSH tunnel: GET `/models` returned HTTP 200 and listed `cx/gpt-6-luna`. On the VPS itself, loopback port 12128 is not listening; its 9Router service answers at `http://127.0.0.1:20128/v1` (GET `/models` HTTP 200). Therefore the VPS-hosted bot must use port 20128, while 12128 is only the workstation-side tunnel. These GET checks do not validate completion auth or trigger a model call.
- User selected the VPS loopback route. Both the workspace `.env` and VPS `.env` now use `http://127.0.0.1:20128/v1` as the base URL (without `/models`). The VPS returned HTTP 200 for GET `/v1/models` and lists `cx/gpt-6-luna`; this endpoint also responds without Authorization, so key validity for completions remains unverified. Provider and trade execution remain disabled. The workspace validator was updated to permit HTTP only on loopback and the full test suite passed (32 tests); that source change has not been deployed to the VPS checkout.
- At this 2026-11-05 check, no enforceable monthly spend cap was found, and no Forex runtime service or compiled EA existed. The user later accepted uncapped charges; a one-request connectivity smoke test and the resulting state are recorded below.
- Before dedicated-key setup, the API key in the Forex `.env` matched the active 9Router key named `Hermes Codex Auto`, rather than a Forex-specific key. The local usage ledger associated that shared key with 21,664 requests and approximately USD 1,374.15 in recorded cost from 2026-07-17 through 2026-11-03; those totals cover shared activity and are not attributable to Forex. No new request was made with that key.
- The admin API requires a dashboard login (`GET /api/keys` returned HTTP 401 without a dashboard session); no authentication bypass was used.

## Dedicated key setup (2026-11-05)

- With the user's explicit approval, a separate active API key named `ForexDemo` was created in the authenticated 9Router dashboard and installed into the workspace and VPS `.env` files without printing it. A read-only database check confirmed the key name and active status; it has zero usage so far.
- At key setup time, the dashboard's global `Require API key` switch was off. `/v1/models` responds without authentication and cannot verify bearer-key validity. No completion request was made during key setup.

## Require API key verification (2026-11-06)

- Inspected the installed 9Router build: `requireApiKey` is a global setting, with no per-key equivalent in this version. The service binds to `127.0.0.1:20128`; recent seven-day usage history showed all 268 requests associated with the existing active `Hermes Codex Auto` key and none without a key.
- Created a SQLite online backup at `~/.9router/backups/data.sqlite.pre-require-api-key-20261105T225935Z`, enabled the global setting, and restarted `9router.service`. Service returned to active state.
- Verified against `POST /v1/chat/completions` using an intentionally empty JSON body: no key returned HTTP 401 `Missing API key`; an invalid key returned HTTP 401 `Invalid API key`; the `ForexDemo` key returned HTTP 400 `Missing model`, confirming authentication passed before request validation. No model was specified, so no model inference or billable completion was requested.
- `/v1/models` still returns HTTP 200 without a key in this build; do not use that metadata endpoint as the authentication check. The setting is global, so any future client calling protected API routes must supply an active 9Router key.
- `MODEL_PROVIDER_ENABLED=false` and `TRADING_EXECUTION_ENABLED=false` remain in the VPS `.env`. The Python event-polling runtime and compiled EA remain unfinished; no trade was sent.

## 9Router model smoke test (2026-11-06)

- The user explicitly accepted model API charges without a dollar cap. No 9Router per-key or monthly hard cap was found. The project retains at most five model calls per day as an operational request-rate guard; this is not a spend cap.
- Sent one minimal `cx/gpt-6-luna` chat completion from the VPS using the `ForexDemo` key; the local 9Router endpoint returned HTTP 200 and the expected smoke response. This incurred provider usage. No news context, trading signal, MT5 order, or trading decision was sent.
- `src/forex_demo/llm_client.py` now contains a bounded-timeout OpenAI-compatible client. It has not been deployed to the VPS. Automatic news polling/runtime is not implemented, so `MODEL_PROVIDER_ENABLED=false` remains appropriate until that runtime is installed and verified. `TRADING_EXECUTION_ENABLED=false` remains unchanged.

## News observer service deployment (2026-11-06)

- Installed `/etc/systemd/system/forex-demo.service`, enabled at boot, running as `saidadam28` with systemd state directory `/var/lib/forex-demo` (mode `0700`). The unit is resource-bounded and read-only outside its state directory.
- Deployed the Python news observer entry point and feed parser to `~/forex/src/forex_demo/`; source selection is in `~/forex/config/sources.vps.toml`.
- The VPS can fetch and parse the official ECB RSS feed. Fed and BLS feed endpoints returned HTTP 403 from this VPS and are excluded from the active source list pending a reachable official endpoint.
- First poll processed 15 feed event IDs; after a service restart, a second poll processed 0 duplicates. SQLite reports `feed:ecb-press=OK` and `news_observer=OK`. Unit reports enabled and active.
- This is a news observer only: no price/position bridge from MT5 is connected, so `MODEL_PROVIDER_ENABLED=false` remains set; health logs report zero model calls and trading disabled. It does not claim to run an AI trader or provide complete USD+EUR news coverage.
- Local project tests after these changes: 41 passed. The VPS `forex-demo.service` itself was also restarted and verified active.
- The unmodified pinned EA31337 source initially produced 100 errors and 60 warnings in the current MetaQuotes compiler. A version-locked compatibility patch now compiles the Lite, Advanced, and Rider modes with 0 errors and 0 warnings each; see `docs/operations/ea31337-compiler-compatibility.md`. The compiled test binaries remain in the scratch build area: no `EA31337.ex5` was installed into the active terminal or attached to a chart. The existing `.ex5` files under the terminal are MetaQuotes example indicators only.
- MT5 `OnInit`/`OnTick` was not changed; no EA was attached, no model-triggered signal was evaluated, and no order was sent.

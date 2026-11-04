# Forex Demo Runtime Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task by task.

**Goal:** Build a shadow-first Python decision service and an EA-side adapter for demo-only Finex MT5, based on an audited, pinned EA31337 revision.

**Architecture:** Python polls explicitly approved public economic/news sources and snapshots market context, calls 9Router only for eligible events, validates structured proposals, and writes them atomically to a local bridge. An EA adapter consumes proposals and independently enforces account, symbol, sizing, stop, spread, daily-loss, drawdown, and duplicate-order controls. Initial mode is shadow and cannot send orders.

**Tech Stack:** Python 3, SQLite, JSON schema, system-independent local file IPC, MetaTrader 5 / MQL5, EA31337 GPL-3.0 source pinned after audit.

**Spec:** `docs/superpowers/specs/2026-11-04-forex-demo-bot-design.md`

## Global Constraints

- 9Router/model use is optional until endpoint/model availability and a hard USD 5/month cap are verified.
- During shadow mode: maximum 5 model calls/day; if cost caps cannot be enforced, disable API calls.
- Proposed demo limits: 0.10% equity initial risk per position, 0.50% daily equity loss, and 2.0% phase drawdown; do not treat these as live-account recommendations.
- Maximum one open position for the initial symbol; no martingale, grid, averaging down, or increasing risk after a loss.
- A stale or invalid signal, failed API, failed feed, stale equity, disconnection, or non-demo account means no new order.
- The bridge is local only; never expose it on a public network interface.
- Every proposal and rejection is timestamped and auditable; secrets are redacted.

## Review Focus

- Duplicate/stale signal after restart: use persisted event identifiers and expiry; cover with replay checks.
- Malformed or adversarial headline/model output: schema validation and source allowlist; cover with parser checks.
- Lot minimum exceeds permitted loss: reject trade; verify with broker symbol specification.
- Model timeout/over-budget/unknown model ID: return WAIT and disable further calls until cooldown/reset.
- EA accidentally accepts a live account or stale equity: fail closed; validate account mode and freshness before considering any order.

---

### Task 1: Audit and pin EA31337

**Files:**
- Create: `third_party/EA31337/` (only after reviewing repository layout and GPL-3.0 obligations)
- Create: `docs/audits/ea31337-audit.md`

**Interfaces:** Audit note records upstream URL, commit SHA, license, dependencies/submodules, supported MT5 build path, and strategy entry/exit/risk interfaces. No adapter may assume an interface before this task is complete.

- [x] Fetch the public repository at a specific commit and record the exact SHA and root license.
- [ ] Review dependency/submodule licenses and build instructions. Initial audit note is in `docs/audits/ea31337-audit.md`; license status for all 130 recursive modules is incomplete.
- [x] Identify the narrowest supported extension point for an adapter and document whether the upstream EA can be used directly. Main entry funnel is virtual `EA::TradeRequest`; upstream cannot be used unmodified for this project's risk requirements.
- [ ] Compile the unmodified EA in an isolated MT5 environment and record the result before making adaptations. No local MetaEditor/MT5/Wine toolchain is present; defer until a controlled compiler environment is available.
- [x] Stop and revise the design if a safe demo-only integration point cannot be identified. A candidate subclass hook exists, but order execution remains disabled pending full audit and compiled validation.

**Current audit status:** partial, not a completed task. See `docs/audits/ea31337-audit.md`. Continue independent schema/service work in shadow mode only; do not enable order functions.

---

### Task 2: Define event, decision, and audit schemas

**Files:**
- Create: `src/forex_demo/schemas.py`
- Create: `schemas/decision-v1.schema.json`
- Create: `docs/adr/0001-local-bridge-and-decision-schema.md`

**Interfaces:** `Decision` contains `event_id`, `created_at_utc`, `valid_until_utc`, `symbol`, `timeframe`, `action`, `confidence`, `strategy_profile`, `reason_code`, and `source_ids`. `action` is one of `BUY|SELL|HOLD|CLOSE|WAIT`; `strategy_profile` is allowlisted. The schema cannot express lot size or risk overrides.

- [x] Define strict required fields, UTC timestamp format, enum values, and maximum field lengths.
- [x] Reject additional fields so model output cannot smuggle execution parameters.
- [x] Define an audit record that stores source identifiers, prompt/schema/model versions, parsed decision, rejection reason, and latency with secrets redacted.
- [x] Verify schema rejects missing fields, invalid enum values, expired decisions, and attempts to add lot/SL/risk overrides.

---

### Task 3: Build persistent event and audit state

**Files:**
- Create: `src/forex_demo/state.py`
- Create: `src/forex_demo/models.py`
- Create: `data/README.md`

**Interfaces:** `StateStore.claim_event(event_id, source_id, published_at_utc) -> bool`, `StateStore.record_decision(record)`, `StateStore.get_last_processed(source_id)`, and `StateStore.record_runtime_health(component, status, updated_at_utc, detail)` persist dedupe, audit, and health state across restarts.

- [x] Create SQLite tables for source cursors, event deduplication, decisions, and runtime health.
- [x] Use transactions for event claims and append-only decision audit records.
- [x] Store UTC timestamps and document retention without secrets; automatic deletion stays disabled until a retention policy is approved.
- [x] Verify duplicate claims remain rejected after reopening the database.

---

### Task 4: Implement public feed collection and eligibility filters

**Files:**
- Create: `src/forex_demo/feeds/base.py`
- Create: `src/forex_demo/feeds/mt5_calendar.py`
- Create: `src/forex_demo/feeds/official_releases.py`
- Create: `src/forex_demo/eligibility.py`
- Create: `config/sources.example.toml`

**Interfaces:** `FeedItem` includes stable `source_id`, `event_id`, `published_at_utc`, `currency_tags`, `importance`, and text summary. `is_eligible(item, now_utc, allowlist, currencies) -> EligibilityResult` rejects stale, duplicate, unknown-source, or irrelevant items. Public feed configuration uses TOML parsed by Python's standard library.

- [ ] Implement adapters only for sources whose public access terms and timestamp behavior have been checked. Parser/config are implemented; ECB reuse terms remain unresolved, so live polling is not enabled.
- [x] Normalize server timezone and daylight-saving offsets to UTC; preserve original timestamps for audit.
- [x] Add allowlist, deduplication storage, freshness window, and currency relevance filters. News pause rules remain for EA adapter.
- [ ] Use fixtures to verify stale, future-dated, duplicate, malformed, and disallowed-source items are rejected. Stale/future/disallowed are covered; malformed and duplicate need explicit feed fixtures.
- [ ] Keep paid feeds disabled by default.

---

### Task 5: Implement bounded 9Router client and shadow decision pipeline

**Files:**
- Create: `src/forex_demo/llm_client.py`
- Create: `src/forex_demo/prompt.py`
- Create: `src/forex_demo/decision_service.py`
- Create: `.env.example`
- Create: `config/runtime.example.yaml`

**Interfaces:** `ModelClient.propose(context) -> Decision`; `DecisionService.process(event, market_snapshot) -> ProcessingResult`. Secrets are loaded from process environment or protected secret storage, never `.env.example` or source control.

- [x] Load and validate demo/shadow, broker, server, symbol, and timeframe from local `.env`; reject real mode, order execution, and enabled model provider. The API key is ignored by the loader and never retained in config objects.
- [ ] Verify model ID and non-trading API compatibility only after the exposed key has been revoked and replaced outside chat.
- [ ] Require enforceable usage limit ≤ USD 5/month and ≤5 calls/day; otherwise set provider disabled.
- [ ] Apply one request per eligible event/symbol/candle, strict timeout, no unbounded retries, and cooldown after errors. Current prototype deduplicates and counts only in process memory; persistence, HTTP timeout, and cooldown await the disabled provider client.
- [x] Validate JSON against the strict schema and map exceptions/stale responses to WAIT. Confidence threshold policy remains to be set from shadow evidence.
- [x] Keep shadow mode as the only implemented mode; proposal result has no bridge or order command interface.
- [ ] Verify disabled provider, timeout, malformed response, excessive-call attempts, and quota denial all result in WAIT with no bridge command. Disabled, provider exception, malformed result and daily cap are unit-covered; API quota is unavailable.

---

### Task 6: Build atomic local bridge and MT5-side risk adapter

**Files:**
- Create: `src/forex_demo/bridge.py`
- Create: `mql5/ForexDemoAdapter.mq5`
- Create: `mql5/include/DecisionSchema.mqh`
- Create: `mql5/include/RiskGate.mqh`
- Modify: `docs/audits/ea31337-audit.md`

**Interfaces:** Python atomically writes one validated proposal file to the terminal's configured common-files directory. Integration must use a custom `EA31337` subclass that overrides the upstream virtual `TradeRequest` open-order funnel, called from the EA's normal signal processing. EA reads only complete, versioned files; `RiskGate` checks demo account, symbol/timeframe allowlist, expiry, duplicate ID, one-position rule, current equity freshness, lot minimum/step, SL distance, spread, daily loss, and phase drawdown. Shadow mode logs a hypothetical accept/reject but cannot call trade-send functions. Before enabling demo execution, audit every other order-open route, including Advanced tasks, and disable or guard each route.

- [ ] Confirm exact bridge directory and MT5 file access mode in the isolated terminal; keep paths configurable and local.
- [ ] Write with temporary file plus atomic rename; include event ID, schema version, and expiry.
- [ ] Implement a custom `EA31337` subclass overriding `TradeRequest`; keep the upstream checkout unchanged and store the integration patch separately.
- [ ] Implement fail-closed validation in the EA adapter and make order execution compile-time or explicit configuration disabled in shadow builds.
- [ ] Add proposed demo risk calculations and skip a trade if minimum lot would breach the cap.
- [ ] Audit and disable/guard every alternate entry path, including Advanced tasks and pending-order actions.
- [ ] Verify malformed/partial/stale/duplicate files, wrong account mode, stale equity, high spread, daily stop, drawdown stop, and minimum-lot rejection.
- [ ] Confirm no trade-send call is reachable in shadow configuration.

---

### Task 7: Produce demo shadow reporting and mobile observability

**Files:**
- Create: `src/forex_demo/report.py`
- Create: `docs/operations/shadow-report.md`
- Modify: `mql5/ForexDemoAdapter.mq5`

**Interfaces:** Daily report aggregates eligible events, model proposals, rejections, hypothetical orders, latency, API usage, PnL replay fields, and risk-gate outcomes. MT5 push notifications cover health/error/guardrail events only; they do not expose credentials.

- [ ] Add daily and per-event summaries with baseline-vs-model labels and costs.
- [ ] Add clear stale data/API disabled/quota reached/runtime disconnected status.
- [ ] Configure and manually verify MT5 push from demo terminal to the user's mobile after a MetaQuotes ID is entered locally.
- [ ] Verify report consistency against stored records and ensure secrets are absent.

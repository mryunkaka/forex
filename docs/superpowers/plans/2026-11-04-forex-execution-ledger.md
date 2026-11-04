# Execution ledger

Plan set:
- `2026-11-04-forex-skill-implementation-plan.md`
- `2026-11-04-forex-demo-runtime-implementation-plan.md`
- `2026-11-04-forex-vps-deployment-plan.md`

Ruling: The requested workspace is not a Git repository and has no current branch/worktree; continue in the user-designated workspace rather than initialize Git or copy the project elsewhere — this preserves the explicitly selected project path and avoids changing repository metadata — cost if wrong: changes do not have branch-level rollback, so each phase must be reviewed and recorded carefully.

Task 1 (skill): completed. Created `.codex/skills/forex-demo-trading/` and its two references. Baseline pressure scenarios were answered without accessing accounts or networks; with-skill scenario review confirmed the required demo-only, secret-rotation, and no-CAPTCHA behaviors. `quick_validate.py` passed after running through an ephemeral `uv` environment with PyYAML (`Skill is valid!`).

Task 2 (discoverability): completed. Skill frontmatter and relative reference links validated; official OpenAI documentation includes `.codex/skills/<skill>/SKILL.md` as a repo-scoped pattern: https://developers.openai.com/blog/eval-skills.

VPS blocker: do not use the previously pasted credentials. Rotation and secure local entry are required before any SSH/API activity. No VPS connection or trade action has been made.

Runtime audit in progress: upstream `src/EA31337.mq5` creates an `EA31337` instance and delegates `OnTick` to it. The EA's inherited `TradeRequest` is virtual and is the visible main signal-open funnel. Ruling: the integration plan now requires a custom subclass to override that funnel and a source audit of all alternate open-order/task paths before any demo execution — this keeps upstream source unmodified and places the AI/risk gate in the normal order route — cost if wrong: an unguarded alternate order path could bypass the model/risk checks, so no order-capable build may be enabled until the audit confirms full coverage.

Task 4 configuration ruling: use TOML rather than YAML for the source allowlist because Python 3.11+ includes a TOML parser in the standard library — this avoids an extra runtime parser dependency and keeps the feed configuration small — cost if wrong: an operator expecting YAML would need to convert the file, but the example remains documented and no user-supplied format preference exists.

EA31337 checkout: root commit `9b9bd38c4e49dd6916f4fe3936e50e97fca7a692`, GPL-3.0. Recursive submodules are present locally; per-module license/build audit remains incomplete. The EA cannot be compiled on this host because MetaEditor/MT5/Wine is unavailable.

Runtime progress: strict schemas, SQLite state, official RSS parser/config, eligibility filters, and a provider-injected shadow decision service are implemented. The model provider stays disabled; only daily call count and schema checks exist, not a real API client or hard monthly-cost enforcement. `.env.example` contains placeholders only. No 9Router call, VPS login, MT5 connection, or order has been performed.

Local verification: `uv run python -m pytest -q` passed (19 tests). The sample TOML source config parsed. A repository scan found no strings matching the previously pasted API-key/password formats. `.gitignore` now excludes `.env`, virtualenv, Python caches, local databases, and runtime artifacts. The service's dedupe and daily counter are process-local; do not treat these as restart-safe quota controls.

Local configuration continuation: `.env` has confirmed `MT5_EXPECTED_SERVER=FinexBisnisSolusi-Demo`, `MT5_SYMBOL=EURUSD`, demo account mode, shadow trading mode, order execution false, and model provider false. Added `runtime_config.py`, which parses only supported settings, ignores API-key/unrelated keys, and rejects unsafe switches. This is a validation utility; no MT5 terminal/service runner is wired yet and it does not connect to the broker.

Feed-source ruling: Fed and ECB provide official RSS listings, and BLS exposes an official CPI RSS feed. ECB site-wide terms contain broad copyright restrictions; RSS availability does not prove unrestricted reuse. Keep live ECB polling disabled until its applicable reuse terms are clarified. Sources: https://www.federalreserve.gov/feeds/feeds.htm ; https://www.ecb.europa.eu/home/html/rss.et.html ; https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html ; https://www.bls.gov/developers/termsOfService.htm.

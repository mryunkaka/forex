# Forex Demo Trading Skill Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task by task.

**Goal:** Create a local Indonesian Codex skill that guides safe research, implementation, and review of the EA31337-based Finex demo project.

**Architecture:** The skill is documentation and workflow guidance only. It reads the approved design, directs later tasks to keep risk controls deterministic, and requires demo-only operation and review gates. It does not contain broker credentials or execute trades.

**Tech Stack:** Markdown; Codex skill format.

**Spec:** `docs/superpowers/specs/2026-11-04-forex-demo-bot-design.md`

## Global Constraints

- Use Indonesian for user-facing guidance.
- Demo only; no route to live orders, deposits, withdrawals, or account switching.
- Risk thresholds are the proposed values in the spec and remain user-reviewable.
- Never store credentials in the repository, prompts, screenshots, or logs.
- No guarantee of profit; do not recommend increasing risk to accelerate results.

## Review Focus

- Skill accidentally treats demo passage as approval for real trading: include explicit permanent demo-only boundary.
- User pastes API/SSH secrets into project: provide rotation and secret handling steps without echoing values.
- User asks for inaccessible private groups or CAPTCHA bypass: guide toward accessible public sources.
- Research claims confuse stars/backtests with evidence of profit: require source/date and evidence-quality notes.
- Risk proposals become fixed without user agreement: label thresholds as proposed until explicitly approved.

---

### Task 1: Create the project skill and reference checklists

**Files:**
- Create: `.codex/skills/forex-demo-trading/SKILL.md`
- Create: `.codex/skills/forex-demo-trading/references/research-and-evidence.md`
- Create: `.codex/skills/forex-demo-trading/references/demo-safety-checklist.md`

**Interfaces:** The skill consumes the approved design spec and produces a repeatable workflow for future Codex tasks. The safety checklist uses the proposed risk settings and acceptance gates from the spec without silently changing them.

- [x] Write skill frontmatter with name, description, invocation boundary, and Indonesian operating instructions.
- [x] Document research-source hierarchy: official broker/platform docs, primary repositories, peer-reviewed research, then clearly labeled public community anecdotes.
- [x] Add required source/date/caveat logging for performance claims and explicit prohibition on private group access or CAPTCHA bypass.
- [x] Add demo-only checklist covering account identity, symbol constraints, stop loss, spread, position sizing, daily/equity stops, stale data, API failure, and manual kill switch.
- [x] Review the skill files for consistency with the design spec and confirm they contain no credentials or unapproved live-trading steps.

---

### Task 2: Validate skill discoverability and instructions

**Files:**
- Modify: `.codex/skills/forex-demo-trading/SKILL.md`
- Verify: `.codex/skills/forex-demo-trading/references/*`

**Interfaces:** Codex loads the skill by its frontmatter and follows its references by paths relative to the skill directory.

- [x] Check markdown links and relative reference paths.
- [x] Confirm the skill can be invoked by name and its instructions do not imply a profitability guarantee.
- [x] Confirm no VPS or API operation is triggered by merely reading or invoking the skill.

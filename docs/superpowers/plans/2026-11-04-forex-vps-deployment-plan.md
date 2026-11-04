# Forex Demo VPS Deployment Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task by task.

**Goal:** Deploy the already reviewed shadow-first demo runtime on the user's Ubuntu VPS, then enable demo order execution only after separate shadow-report review.

**Architecture:** First inventory the VPS read-only. Install MT5 desktop under Wine only if supported. Run Python as a least-privilege systemd service; keep the bridge loopback/local-files only. Configure secrets outside the repository and connect the same Finex demo account to desktop and mobile. No live credentials or live order path.

**Tech Stack:** Ubuntu, systemd, Wine/MetaTrader 5, Python virtual environment, SQLite, MT5 Android push.

**Spec:** `docs/superpowers/specs/2026-11-04-forex-demo-bot-design.md`

## Global Constraints

- Do not reuse SSH password or 9Router API key previously pasted in chat; revoke/rotate before connecting.
- Prefer a fresh SSH key installed by the user; do not ask the user to paste replacement secrets into chat.
- Initial remote inspection is read-only and reports OS, CPU, RAM, disk, architecture, display/session, and network status.
- Install only after VPS meets the verified terminal and service requirements.
- Demo account only; verify account number/server/type in terminal before any order-capable configuration.
- Do not expose bridge/API ports publicly; firewall changes are out of scope unless reviewed separately.
- Keep systemd service unprivileged, restart-bounded, and logs redacted.

## Review Focus

- Existing VPS data or services are overwritten: inspect paths and services before changes; preserve unrelated state.
- Reboot/session disconnect stops MT5 GUI: verify desktop/session persistence and recovery before enabling demo execution.
- Credentials leak through shell history/systemd/logging: use protected credential files/environment and verify redaction.
- Wrong account/server selected: perform manual demo account confirmation and retain a startup fail-closed check.
- Restart loop or unavailable API causes repeated calls: enforce backoff and request ceilings.

---

### Task 1: Establish secure access and perform read-only inventory

**Files:**
- Create: `docs/operations/vps-inventory.md`

**Interfaces:** Inventory contains only non-secret facts and redacted command output.

- [ ] Revoke/rotate the previously exposed SSH password and API key; install a fresh SSH public key using the user's secure method.
- [ ] Connect with host-key verification; do not disable SSH host-key checks.
- [ ] Run read-only commands for OS/version, architecture, vCPU, RAM, free disk, display session, network, current services, and package manager state.
- [ ] Record compatibility findings and stop if the environment cannot keep MT5 and the worker alive after disconnect/reboot.

---

### Task 2: Prepare least-privilege service environment

**Files:**
- Create on VPS: `/opt/forex-demo/`
- Create on VPS: `/etc/systemd/system/forex-demo.service`
- Create on VPS: protected environment file under `/etc/forex-demo/`

**Interfaces:** systemd runs as a dedicated unprivileged account; environment file mode is 0600 and excluded from logs/backups not protected by policy.

- [ ] Create dedicated service user and app directory without modifying unrelated accounts or services.
- [ ] Install only pinned Python dependencies into a virtual environment.
- [ ] Configure service restart limits, working directory, restrictive filesystem/network permissions, and bounded logs.
- [ ] Verify service starts in provider-disabled shadow mode without any credentials.

---

### Task 3: Install and configure MT5 demo terminal

**Files:**
- Create on VPS: MT5 terminal installation under a dedicated user profile.
- Create on VPS: EA/adapter files under the terminal's data directory.

**Interfaces:** MT5 connects only to the user's Finex demo server; MT5 common-files path matches the Python bridge configuration.

- [ ] Install Wine/MT5 only if the read-only inventory meets requirements.
- [ ] Sign in manually to the Finex demo account; verify account type/server and phone login separately.
- [ ] Install the pinned/audited EA and shadow adapter; leave order execution disabled.
- [ ] Confirm terminal and adapter recover after session disconnect and reboot.
- [ ] Verify desktop and MT5 mobile show the same demo account and mobile receives push alerts.

---

### Task 4: Configure rotated API key and bounded model access

**Files:**
- Modify on VPS: protected environment file only.
- Verify: service logs and 9Router usage page.

**Interfaces:** The service may call the verified model only when operator-controlled spend cap ≤ USD 5/month and ≤5 calls/day are active; otherwise provider stays disabled.

- [ ] Enter the newly issued API key locally on VPS without transmitting it in chat or writing it to repository files.
- [ ] Confirm model ID, endpoint response shape, usage tracking, and enforceable cap using a non-trading health request.
- [ ] If any control cannot be enforced, keep LLM disabled and continue mock/offline shadow operation.
- [ ] Verify errors and usage limits do not trigger retries beyond configured maximum.

---

### Task 5: Observe shadow mode and consider demo order activation

**Files:**
- Create: `docs/operations/vps-shadow-review.md`

**Interfaces:** Shadow report contains no secrets and is reviewed before any order-capable mode is enabled.

- [ ] Run shadow service and terminal for the spec's minimum observation period; verify event logs, local bridge, restart behavior, mobile status, daily usage, and no order sends.
- [ ] Compare AI proposals to baseline signals with timestamped data and realistic costs.
- [ ] Present the report and obtain the user's explicit approval before changing the EA to demo order execution.
- [ ] After approval, enable demo-only order path with exact proposed risk caps; verify account guard and kill switch before the first demo order.
- [ ] Keep real-account switching and live orders disabled.

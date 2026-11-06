# Forex demo observer service

`forex-demo.service` continuously polls the VPS-reachable official ECB RSS feed, deduplicates event IDs in SQLite, and records source/runtime health. It runs as the unprivileged `saidadam28` account and is enabled at boot.

```bash
sudo systemctl status forex-demo.service
journalctl -u forex-demo.service -f
sudo systemctl restart forex-demo.service
```

Database: `/var/lib/forex-demo/state.sqlite3` (directory mode `0700`). Active source list: `~/forex/config/sources.vps.toml`.

This service is intentionally **news observation only**. It has no MT5 quote/position bridge, makes no LLM calls, and cannot place or manage orders. The service's `OK` status means the configured feed was fetched, parsed, and persisted successfully. It does not mean the AI trading system or EA31337 is ready. Fed and BLS feed endpoints returned HTTP 403 from the VPS at deployment and are currently omitted.

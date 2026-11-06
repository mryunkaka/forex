"""CLI entry point for the shadow-safe news observer."""

from __future__ import annotations

import argparse
import logging

from forex_demo.runtime import build_observer, run_forever


def main() -> None:
    parser = argparse.ArgumentParser(description="Forex demo news observer (no model calls or trades)")
    parser.add_argument("--sources", default="config/sources.example.toml")
    parser.add_argument("--database", default="data/forex-demo.sqlite3")
    parser.add_argument("--env", default=".env", help="protected runtime environment file")
    parser.add_argument("--snapshot", default=None, help="MT5 common-files snapshot CSV")
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--once", action="store_true", help="poll once and exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    observer = build_observer(args.sources, args.database, env_path=args.env, snapshot_path=args.snapshot)
    if args.once:
        result = observer.poll_once()
        if result["failures"]:
            raise SystemExit(1)
    else:
        run_forever(observer=observer, interval_seconds=args.interval)


if __name__ == "__main__":
    main()

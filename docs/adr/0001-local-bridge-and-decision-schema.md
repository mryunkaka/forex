# ADR 0001: Strict proposal schema and local file bridge

Status: Accepted for local shadow implementation; MT5 path mapping remains unverified until a terminal is installed in an isolated environment.

## Context

The Python service and MT5 terminal will run on the same Ubuntu VPS. A public HTTP bridge would expose an unnecessary network surface. Model output is untrusted input and must not contain broker execution parameters.

## Decision

- Use versioned JSON `decision-v1` with `additionalProperties: false`; only the fields in `schemas/decision-v1.schema.json` are accepted.
- Write accepted proposals to a local file in the MT5 terminal's Common/Files directory using temporary-file-plus-atomic-rename. The exact path is configured at installation and verified against that terminal.
- The EA is responsible for the final risk check. JSON `action` and strategy profile do not encode lot, SL/TP, leverage, or risk settings.
- Start in shadow mode; file output is a record of a proposal, not permission to trade.

## Consequences

- No bridge port needs to be exposed to the network.
- Python and MQL5 must share exact schema version, timestamp semantics, and expiry handling.
- Atomic rename and file permissions must be validated under Wine/Ubuntu before the adapter is considered operational.
- This decision does not claim that MT5 or Wine has been installed or tested.

# EA31337 audit — initial source inspection

Status: partial. Source downloaded for review; no EA binary compiled or installed. This note is not a full license audit or sign-off to enable order execution.

## Source identity

- Repository: https://github.com/EA31337/EA31337
- Checkout commit: `9b9bd38c4e49dd6916f4fe3936e50e97fca7a692` (`master` HEAD at fetch time)
- Root license: GNU GPL-3.0
- Root submodules initialized recursively: 130 entries across wiki, classes, indicators, strategies, and meta strategies.
- Root README describes EA31337 as an MT4/MT5 Forex robot/framework, says default inputs are optimized for EURUSD, and recommends backtesting/demo per broker-symbol combination.

## Relevant MQL5 control flow

- `src/EA31337.mq5` constructs `EA31337` in `OnInit()` and calls `ea.OnTick(...)` from `OnTick()`.
- `EA31337` derives from `EA`; the visible main strategy open route in `EA::ProcessTick` calls the virtual `TradeRequest(...)` method.
- The base `TradeRequest` creates a market request, sets volume to the strategy lot size floored at the broker's minimum lot, invokes `Strategy::OnOrderOpen`, and sends through `Trade::RequestSend`.
- `Trade::GetTradeOpenRequest` builds a market request but does not itself attach a broker-side initial SL/TP. `Strategy::OnOrderOpen` in the inspected base code configures close conditions such as time, loss, and profit. Additional dynamic stops exist elsewhere in the framework and still require a full path audit.
- `EA31337.mq5` has an empty `OnTimer()`. The Lite inputs show defaults on several timeframes; M5 is not the only active timeframe in the stock defaults.

## Consequences for this project

- Do not install stock EA31337 defaults or any `.set` file as an order-capable Finex strategy.
- A possible AI gate is a custom `EA31337` subclass overriding the virtual `TradeRequest` funnel, but the exact strategy-signal-to-model matching, stop placement, volume sizing, and all alternate entry paths must be proved in a compiled isolated build.
- The model decision alone cannot safely satisfy the planned 0.10% risk cap. The adapter must calculate loss at an actual mandatory broker-side SL using Finex tick/contract data and reject if 0.01 lot exceeds the cap.
- Advanced tasks, pending orders, and any direct `RequestSend`/trade-action route must be disabled or guarded. The initial profile must be explicitly one symbol and M5, rather than stock multi-timeframe defaults.

## Dependencies and license review

- The root has five direct submodules and 130 recursive submodule entries at this pinned commit.
- A local scan found root-level `LICENSE`, `COPYING`, or `NOTICE` text in only 3 of those 130 checked-out submodule directories. Some other repositories advertise GPL-3.0 in their README badges or file headers, but that does not complete a per-component license audit.
- Before redistributing binaries or making this a bundled product, verify the license for every source file/submodule included in the compiled EA. Keep source notices and applicable license text with any redistributed derivative.

## Build and environment status

- No `metaeditor64.exe`, MT5 terminal, Wine, or `make` executable was found on the local Windows host during inspection.
- The upstream Makefile expects a MetaEditor toolchain (and its own documented compiler workflow). No compile was performed; no EA has been placed in a terminal.
- VPS inventory and compilation remain blocked until the VPS access credentials are rotated and a secure SSH key path is established.

## Go/no-go

**Go:** continue schema, feed, shadow service, and local bridge development with orders impossible/disabled.

**No-go:** compile/install an order-capable EA, run a Finex demo trade, or enable 9Router calls until (1) all required submodules are cleanly pinned and license status reviewed, (2) the custom order gate and alternate routes are audited and compiled, (3) Finex contract/lot/SL risk calculations are verified, and (4) rotated credentials and a safe VPS environment are available.

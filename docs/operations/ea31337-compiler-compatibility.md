# EA31337 compiler compatibility

The pinned EA31337 source and its nested classes/strategy submodules use implicit
conversions, iterator conversions, and structure assignments that the current
MetaEditor compiler rejects. Keep the upstream pins unchanged and apply the
project compatibility patch after initializing submodules:

```powershell
git submodule update --init --recursive
powershell -ExecutionPolicy Bypass -File .\tools\apply_ea31337_compat.ps1
```

The patch is version-locked to the EA31337 and nested submodule commits recorded
in `tools/apply_ea31337_compat.ps1`. It changes only those pinned source trees.
If an upstream pin changes, regenerate and verify a patch for the new source
before applying this one.

The compatibility changes replace invalid signed position references with
unsigned indices, keep dictionary iterators in their base type or return the
object iterator type, copy MQL date and trade structures field by field, retain
base pattern-flag checks in pattern subclasses, and use typed constructors for
data values. The regression check is a full EA31337 MT5 compile using the
project's current MetaEditor installation. A successful compile does not
validate strategy performance or make the EA suitable for live trading.

## Verification (2026-11-06)

Using the current MetaEditor on the VPS, the patched source compiled all three
published modes in a scratch build directory:

| EA31337 mode | Result |
| --- | --- |
| Lite | 0 errors, 0 warnings |
| Advanced | 0 errors, 0 warnings |
| Rider | 0 errors, 0 warnings |

The resulting test binaries stayed in the scratch build area. No EA31337 binary
was copied into the active MT5 installation or attached to a chart. This
verification covers compilation only; strategy behavior still requires
backtesting and demo forward testing.

# Experimental bounded object ID enumeration (v1)

This implementation is **read-only** and independent of manual GUI selection.
It probes an explicitly supplied half-open Object ID interval, at most 256 IDs
per request. This is **not** full world enumeration: table capacity, ID reuse,
and concurrent mutations remain unverified. The known World+0x0E8 index is
looked up through the existing HDObjectAPI. No new offsets are introduced.

## Python example

```python
from aoe2hdcontrol.object_api import WindowsProcessReader, HDObjectAPI
from aoe2hdcontrol.object_enumeration import enumerate_known_id_window

with WindowsProcessReader(1234) as reader:
    api = HDObjectAPI(reader, allow_candidates=True)
    report = enumerate_known_id_window(
        api, start_id=2000, stop_id=2200,
        class_id=4, own_only=True
    )
    print(report)
```

Replace PID and ID window with verified values from the **current** session.
No unit selected in the game's UI is required. Only known classes 3/4/6
are accepted, and ownership must resolve to the local player by default.
Failures and mismatches are reported without aborting the entire probe.
No command dispatch, memory write, DLL injection, or movement is performed.

## Evidence and limitations

- Canonical source: AoE2HD.mapping, World+0x0E8 (ID lookup), Object+0x08
  (candidate ID), Object+0x10 (candidate ownership), Object+0x078 and
  Object78Target+0x00C (class), ObjectTypeTarget+0x10 (type).
- The user must explicitly enable candidates; results are experimental.
- Reading indices outside the actual allocation is not independently proven
  safe; a bounded window limits but does not eliminate this uncertainty.
- A success only establishes that a particular ID could be resolved at
  observation time, not that an exhaustive inventory was obtained.
- Do not issue commands based on stale IDs. Revalidate ownership before any
  future control action, and record the binary hash plus independent sessions.
- Tests use simulated reader objects, not a running Windows game.

Run: `python -m unittest discover -s tests -v`.

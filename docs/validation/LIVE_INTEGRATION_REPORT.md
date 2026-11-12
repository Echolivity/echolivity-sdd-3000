# Ableton Live 12 integration test report — v1.0.2-rc5

**Status: tested by the owner in Ableton Live 12 Suite (Windows), 2026-11-12, on rc3, the UI test build and rc4.** Results are as reported by the owner; items not listed are not yet run. rc5's new parts (UI-2 fix, triplets, LOOP COMP / CAL) haven't been tested in Live yet.

| Test | Build | Result (owner, Live 12 Suite, Windows; 44.1 kHz, ~48 ms latency) |
|---|---|---|
| L-1 device loads | rc4 | **PASS**: full panel incl. FB ROUTE and RETURN |
| L-1 Max Console | rc3: clean · rc4: **UI-2** | rc4: no red errors, but a continuous flood of `parameter '<unknown>' not found` → **UI-2, fixed in rc5** (bank slots); confirm in rc5 |
| L-15 interface | rc3 → rc4 | **FAIL in rc3 → UI-1** (blank panel); **PASS with the rc4 fix** |
| L-2 sound, no clicks when moving controls | rc4 | **PASS** |
| L-9 HOLD (engage, release, fast re-engage) | rc4 | **PASS** |
| L-7 program memory: WRITE to 6, switch to 3, back to 6 | rc4 | **PASS**: the stored program recalls as set |
| L-5b LFO Mod mapping | rc4 | **PASS (mapping accepted, TIME shown)**. Owner noted the knob "not moving in sync": in Mod mode Live keeps the knob/number at its own value and shows the LFO on the ring only; TIME in glide mode also follows at a limited speed. Documented (Manual). Audible following not separately confirmed |
| L-5c EXT loop routing | rc4 | **PASS**: Live offers ECHOLIVITY 3/4 in both choosers; repeats pass through track B. Repeats arrive late (owner's latency ~48 ms) → **LOOP COMP / CAL added in rc5** |
| L-13 CPU, 8 instances | rc4 | **PASS: no dropouts** (CPU % not recorded) |
| L-7a D-1 `.adv` hot-load | | **not run** |
| L-3, L-4, L-5, L-6, L-7b, L-8, L-10, L-11, L-12, L-14 | | **not run** |
| rc5: L-5d CAL / LOOP COMP, L-6b triplets, UI-2 console | rc5 | **not run** |

Earlier status of this report (static only):

Reason: the validation environment is a Linux workspace without Ableton Live or Max. Running the tests on the requester's own computer was attempted, but no computer was linked to the session. None of the results below were simulated or inferred; the static evidence column only shows what was checked without running Live.

| Brief item | Test | Status | Static evidence available (not a substitute) |
|---|---|---|---|
| A. Load the `.amxd` in Live 12 | L-1 | BLOCKED | container, JSON and amxdtype checked (static check 1) |
| A. Device initialisation | L-1, L-8 | BLOCKED | start-up wiring traced; D-1 fix applied in rc3 (static check); confirm with L-7a |
| A. All controls functional | L-2…L-6, L-9, L-10 | BLOCKED | 33 controls wired to the matching gen~ Params with matching ranges (static) |
| A. Parameter automation | L-4 | BLOCKED | 38 automatable parameters, unique names (static) |
| rc4. External regeneration loop (device I/O 3/4) | L-5c | not yet run | 4-channel plugin~/plugout~ wired (static check); loop simulated in the C build |
| rc3. LFO **Mod** mapping on the continuous knobs | L-5b | BLOCKED | 13 dials declare Modulation Mode Additive; stepped/stored-only declare none (static check) |
| A. Preset loading and saving | L-7, L-7a, L-7b | BLOCKED | **D-1 / D-2 predicted** (`DEFECTS.md`) |
| A. State persistence after closing / reopening the project | L-8 | BLOCKED | Set-load path not affected by D-1 (program logic gated until initialised) |
| A. No Max console errors | L-1 | BLOCKED | GenExpr subset rules pass; all patch cords valid (static) |
| A. No dropouts / unexpected silence | L-13 | BLOCKED | C build stable under automation and HOLD + FB 10 (benchmark report) |
| B. Actual gen~ compilation | L-1 | BLOCKED | the embedded code is byte-identical to the tested source |
| B. Compiled DSP behaves as expected | L-3 | BLOCKED | C translation passes 43/44 (1 known minor, D-3) |
| B. Initialisation, reset, playback | L-1, L-8, L-11 | BLOCKED | engine: no ramps at load; D-3 start-up tap crossfade |
| B. HOLD activation, release, rapid re-engagement | L-9 | BLOCKED | engine: 108-case release matrix, re-engage, mid-fade re-engage PASS |
| B. No stale-buffer playback / discontinuities | L-9 | BLOCKED | engine: release never reads stale memory (tests 37–38) |
| D. Device latency, PDC | L-14 | BLOCKED | patcher declares `latency: 0`; engine direct path 0 samples |
| D. CPU at 44.1/48/88.2/96 kHz, buffer sizes, 8 instances, automation, HOLD + FB | L-13 | BLOCKED | C-build grid only (`PERFORMANCE_REPORT.md`) |
| E. Program re-selection edge case | L-7b | BLOCKED | D-2 analysis |
| E. `.adv` hot-loading edge case | L-7a | BLOCKED | D-1 root-cause trace |
| E. Backward compatibility of Sets / presets | L-7, L-8 | BLOCKED | 158/158 parameter definitions identical to v1.0.1 (static) |

## How to complete this report

Run `docs/LIVE_VALIDATION_CHECKLIST.md` (L-1 … L-15, plus L-7a and L-7b for D-1 and D-2) on a computer with Live 12. Record the Live and Max versions, OS, audio interface, sample rate and buffer size for each result, and attach the Max Console text for L-1.

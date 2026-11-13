# Release decision — ECHOLIVITY SDD-3000 v1.0.2-rc7

## Decision: CONDITIONAL PASS — **not ready for v1.0.2 production release**

No critical defect has been **reproduced**. Ableton Live validation is **partial**:
- The owner ran selected checklist items in Live 12 Suite on Windows on rc3/rc4 (see "Owner's Live 12 results" below).
- The rc6 SEND / RTN routing menus passed all **7** native checks in Live 12.4.6 / Max 9 (`RC6_SEND_RTN_LIVE_TEST.md`).
- The rc7 REVERSE modes have **not** been run in Live (offline engine tests only).
- Every other checklist item is still **not run**.

One **likely high-severity** defect (D-1, `.adv` hot-load) is predicted from the shipped wiring and Cycling '74's documentation and must be confirmed or refuted in Live.

The rc6 result covers **routing only**. It is not evidence about sound quality. rc7 adds REVERSE but leaves the forward signal path bit-identical to rc6, so HW-1 (alias images) and HW-2/HW-3 are exactly as open as before.

*Earlier status (before the owner's rc3 testing, kept for the record):* every mandatory Live item was BLOCKED because no Live/Max environment was available and the requester's computer was not linked. This no longer describes the current state.

**Production release requires all of:**
1. `docs/LIVE_VALIDATION_CHECKLIST.md` executed in Live 12 (L-1 … L-15) with results recorded in `LIVE_INTEGRATION_REPORT.md`.
2. **L-7a (D-1)** passes: the fix is applied in rc3, so the hot-loaded `.adv` must restore TIME 500 / FEEDBACK 6. If it still shows 380 / 3, the decision becomes **FAIL** for preset functionality.
3. **L-5d (CAL / LOOP COMP)**, **L-6b (triplets)** and the UI-2 console check pass in rc5 or later. (L-5b and L-5c passed in rc4.)
4. **L-7b (D-2)** run and dispositioned the same way.
5. Decide on D-3: defer to v1.0.3 (recommended) or fix now (changes start-up output only).
6. **REVERSE** native checks (`REVERSE_LIVE_TEST.md`) pass.
7. A recorded decision on **HW-1** (see "Hardware-reference validation" below), backed by a listening review.

## Release-blocker status (rc7)

| Item | Status | Evidence that closes it |
|---|---|---|
| rc7 REVERSE (OFF / REV / ALT / ALT R) | **Open, not run in Live.** Offline: 6 new engine tests pass; OFF bit-identical to rc6 | `REVERSE_LIVE_TEST.md` checks 1–13 recorded |
| rc6 SEND / RTN routing menus | **PASS** (7/7, Live 12.4.6 / Max 9, device at `c03aabb`) | Closed: `RC6_SEND_RTN_LIVE_TEST.md` |
| L-1 load, L-2, L-7, L-9, L-15, L-5b, L-5c, L-13 (no dropouts) | **PASS** on rc4 (owner, Windows) | Closed for rc4. rc6 changed the panel (new menus), so L-15 is worth a re-look on rc6 |
| UI-2 console flood (fixed in rc5) | **Not formally confirmed.** rc6 test 1 reported a clean Max for Live console on load | Run the L-1 console check on rc6 with the device open in Max, and record it |
| L-7a (D-1 `.adv` hot-load) | **Open, not run** | L-7a result in `LIVE_INTEGRATION_REPORT.md` |
| L-7b (D-2 program re-select) | **Open, not run** | L-7b result and disposition |
| D-3 (first 25 ms after creation) | **Open, decision pending** | Owner decision: defer to v1.0.3 or fix |
| L-5d CAL / LOOP COMP, L-6b triplets | **Open, not run in Live** (simulation only) | L-5d and L-6b results |
| L-3, L-4, L-5, L-6, L-8, L-10, L-11, L-12, L-14; L-13 CPU % | **Open, not run** | Checklist results. rc6 test 5 covered routing persistence only, not the full L-8 Set reopen |
| HW-1 alias images | **Open, not fixed in rc6 / rc7** | A fix merged after its own audit, native test and listening review; or a recorded decision to ship with it documented |
| HW-2, HW-3 | **Open, minor** | Disposition (fix or document) |
| Reproducibility | **6/7**: one FAIL for a stray file (`experiments/hw1/bench_hw1.c`) in the release tree | Remove or relocate the file and re-run `tools/verify_release.py` |

## What was verified (executed)

| Area | Result |
|---|---|
| rc1 package integrity | archive hash matches the published value; 63/63 manifest entries verified |
| DSP regression (C translation of the exact gen~ code) | 43/44 PASS; 1 known minor (D-3, pre-existing since v1.0); all 41 rc1 measurements identical |
| v1.0.1 → rc1 A/B | 47/47 scenarios bit-identical apart from the two intended fixes |
| Static device checks | 20/20 (rc3: +LFO Mod mapping, +D-1 wiring and order; rc4: +UI-1, 4-channel I/O) |
| EXT regeneration loop (C build, simulated routing) | INT bit-identical to rc3; EXT −3.01 dB/pass at RETURN 5 (= FEEDBACK 5); bounded; NaN-safe; click-free switching |
| **Live 12 Suite, Windows (owner)** | device loads, Max Console clean; UI-1 (blank panel) found and fixed, panel now displays |
| **Live 12.4.6 / Max 9 (owner), rc6** | SEND / RTN routing menus 7/7 PASS (`RC6_SEND_RTN_LIVE_TEST.md`) |
| Parameter / preset compatibility vs v1.0.1 (static) | 158/158 definitions identical; factory programs unchanged since v1.0 |
| CPU (C build) | flat across block sizes, automation and HOLD + FB 10; same as v1.0.1 |
| Latency | PDC 0 declared; direct path 0 samples (C build) |
| Reproducibility | 6/7 in the current `docs/REPRODUCIBILITY.json` (1 FAIL: stray `experiments/hw1/bench_hw1.c`). `docs/TEST_REPORT.md` section 7 still shows an earlier 8/8 run |

## Hardware-reference validation (added after rc5; device unchanged)

Against the 1982 Korg documentation, not an original unit (`HARDWARE_REFERENCE.md`): 28 measurements consistent, 5 inconsistent, 9 without a usable documented reference.

- **HW-1 (significant):** the clock-domain conversion creates in-band alias images, for example a 1 kHz image only 10 dB below a 17 kHz tone at a 48 kHz host. Total distortion + noise at 1 kHz is 0.28 % against the SM's 0.03 % typical.
  - Not a functional defect, and the existing engine and static results don't change.
  - It is the largest measured deviation from the documented hardware, and it could colour bright material.
  - **Recommendation:** listen for it (cymbals and hats through long feedback) and decide on a resampler investigation before a production release.
  - **Status at rc6:** not fixed. Remediation candidates exist on separate branches and are not merged; rc6 does not contain them. The rc6 routing validation does not bear on HW-1.
- **HW-2 and HW-3 (minor):** the HIGH cut's top-octave slope, and 17 kHz response marginally beyond −3 dB at 48 / 96 kHz.

Every feature remains **HARDWARE UNVERIFIED**: no original unit was available. The decision stays **CONDITIONAL PASS**.

## Owner's Live 12.4.6 results (rc6)

SEND / RTN menus: load with a clean console, destination and source lists, full EXT loop from the menus, following routing changes made in Live, routing persistence across save / reopen, track rename / add / delete, and unchanged INT mode and factory programs: **7/7 PASS** (`RC6_SEND_RTN_LIVE_TEST.md`). No other checklist item was run in this session.

## Owner's Live 12 results (rc3/rc4)

Load, panel, sound without clicks, HOLD, program memory, LFO Mod mapping, external loop routing and 8 instances without dropouts: **PASS** (`LIVE_INTEGRATION_REPORT.md`). Found and fixed: UI-1 (blank panel, rc4), UI-2 (console flood, rc5). Still open: D-1 `.adv` hot-load (L-7a), automation, Set reopen, sample-rate change, and the new rc5 items.

## What changed in rc7

- **Feature (owner request):** REVERSE menu: REV (every repeat backwards), ALT (forwards first, then alternating), ALT R (backwards first). A separate reverse memory and D/A path, computed only while a mode is on.
- **Unchanged:** REVERSE OFF is bit-identical to rc6 on all outputs; 162/162 existing parameters, Push banks and factory programs identical. One new parameter (Reverse, 163 total) and a new Push bank, not stored in programs.
- **Offline:** engine tests 56/57 (6 new; D-3 known), static checks 20/20, preset compatibility vs rc6 6/6. **Not yet tested in Live.**

## What changed in rc6

- **Feature (owner request):** SEND / RTN menus on the panel select the external-loop send and return tracks through the Live Object Model (`v8.codebox`, Live 12.2+ / Max 9). Live saves the routing with the Set.
- **Unchanged:** gen~ DSP byte-identical to rc5; 162/162 parameters, Push banks and factory programs identical. Engine tests 50/51 (known D-3), static checks 20/20, mock routing test 10/10.
- **Interface:** the WRITE help text moved to the manual to make room for the menus.

## What changed in rc5

- **UI-2 fix** (console flood).
- **Owner requests:** triplet divisions (1/16T, 1/32T appended; musician labels), LOOP COMP + CAL for the external loop. LOOP COMP 0 / old divisions are bit-identical to rc4.
- **Documentation** from the musical evaluation (P1, P3, P5, P6).

## What changed in rc4

- **UI-1 fix** (blank panel in Live, confirmed fixed by the owner).
- **Feature (owner request):** external regeneration loop, FB ROUTE / RETURN, device in/out 3-4. DSP changed only on that path; INT is bit-identical to rc3.

## What changed in rc3

- **Feature (owner request):** Modulation Mode *Additive* on the 13 continuous knobs, so Live's LFO and modulators can map them in **Mod** mode.
- **D-1 fix:** one cord in the start-up sequence plus recall order (Program first).
- **Unchanged:** GenExpr/DSP (byte-identical; all 44 engine tests give the same results), sound, factory programs, parameter names, types, ranges and initial values, interface (`docs/ui_preview.png` byte-identical). Static checks: 19/19.

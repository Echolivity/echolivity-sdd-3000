# Release decision — ECHOLIVITY SDD-3000 v1.0.2-rc5

## Decision: CONDITIONAL PASS — **not ready for v1.0.2 production release**

No critical defect has been **reproduced**. However, every mandatory Ableton Live validation item is **BLOCKED**: no Live/Max environment was available, and the requester's computer was not linked. One **likely high-severity** defect (D-1, `.adv` hot-load) is predicted from the shipped wiring and Cycling '74's documentation and must be confirmed or refuted in Live.

**Production release requires all of:**
1. `docs/LIVE_VALIDATION_CHECKLIST.md` executed in Live 12 (L-1 … L-15) with results recorded in `LIVE_INTEGRATION_REPORT.md`.
2. **L-7a (D-1)** passes: the fix is applied in rc3, so the hot-loaded `.adv` must restore TIME 500 / FEEDBACK 6. If it still shows 380 / 3, the decision becomes **FAIL** for preset functionality.
3. **L-5d (CAL / LOOP COMP)**, **L-6b (triplets)** and the UI-2 console check pass in rc5. (L-5b and L-5c passed in rc4.)
4. **L-7b (D-2)** run and dispositioned the same way.
5. Decide on D-3: defer to v1.0.3 (recommended) or fix now (changes start-up output only).

## What was verified (executed)

| Area | Result |
|---|---|
| rc1 package integrity | archive hash matches the published value; 63/63 manifest entries verified |
| DSP regression (C translation of the exact gen~ code) | 43/44 PASS; 1 known minor (D-3, pre-existing since v1.0); all 41 rc1 measurements identical |
| v1.0.1 → rc1 A/B | 47/47 scenarios bit-identical apart from the two intended fixes |
| Static device checks | 20/20 (rc3: +LFO Mod mapping, +D-1 wiring and order; rc4: +UI-1, 4-channel I/O) |
| EXT regeneration loop (C build, simulated routing) | INT bit-identical to rc3; EXT −3.01 dB/pass at RETURN 5 (= FEEDBACK 5); bounded; NaN-safe; click-free switching |
| **Live 12 Suite, Windows (owner)** | device loads, Max Console clean; UI-1 (blank panel) found and fixed, panel now displays |
| Parameter / preset compatibility vs v1.0.1 (static) | 158/158 definitions identical; factory programs unchanged since v1.0 |
| CPU (C build) | flat across block sizes, automation and HOLD + FB 10; same as v1.0.1 |
| Latency | PDC 0 declared; direct path 0 samples (C build) |
| Reproducibility | see `docs/TEST_REPORT.md` section 7 |

## Owner's Live 12 results (rc3/rc4)

Load, panel, sound without clicks, HOLD, program memory, LFO Mod mapping, external loop routing and 8 instances without dropouts: **PASS** (`LIVE_INTEGRATION_REPORT.md`). Found and fixed: UI-1 (blank panel, rc4), UI-2 (console flood, rc5). Still open: D-1 `.adv` hot-load (L-7a), automation, Set reopen, sample-rate change, and the new rc5 items.

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

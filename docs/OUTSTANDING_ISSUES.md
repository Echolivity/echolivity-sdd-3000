# ECHOLIVITY SDD-3000 v1.0.2-rc7 — Outstanding issues

rc7: REVERSE added (OFF bit-identical to rc6); not yet tested in Live (`docs/validation/REVERSE_LIVE_TEST.md`).

rc6: SEND / RTN routing menus added and passed 7/7 native checks in Live 12.4.6 (`docs/validation/RC6_SEND_RTN_LIVE_TEST.md`). DSP unchanged from rc5; none of the issues below is closed by rc6.

rc3: D-1 fix applied (pending Live confirmation, L-7a); LFO Mod mapping added (L-5b).

Updated by the final validation round: see `docs/validation/` (decision: CONDITIONAL PASS, not production-ready).

| ID | Issue | Status | Blocks final 1.0.2? |
|---|---|---|---|
| OI-1 | **Ableton Live / Max runtime validation incomplete.** Originally none had been executed. The owner has since passed L-1, L-2, L-5b, L-5c, L-7, L-9, L-13 (no dropouts) and L-15 on rc3/rc4 (Windows), and the rc6 SEND / RTN routing checks in Live 12.4.6 (`docs/validation/LIVE_INTEGRATION_REPORT.md`). Still not run: automation, MIDI mapping, tempo sync, `.adv` hot-load (L-7a/L-7b), full Set save/reopen, sample-rate changes, BYPASS, invalid-input recovery, latency, and the rc5 controls (L-5d, L-6b). | PARTIAL. Manual steps in `docs/LIVE_VALIDATION_CHECKLIST.md` | **Yes** |
| OI-2 | **CPU and latency inside Live not measured.** Only the C build was benchmarked (≈3–14 % of one 2.1 GHz Xeon core at 44.1–192 kHz). gen~ code generation, Max scheduling and Live overhead will differ. | NOT VERIFIED | Yes (measure during OI-1) |
| OI-3 | **gen~ `fixnan` semantics.** The NaN protection relies on gen~'s `fixnan` operator replacing NaN with 0, as documented. If gen~ compiled with flags that remove NaN checks, the protection would be ineffective (no audible effect on valid audio either way). | NOT VERIFIED | Yes (checklist item L-12) |
| OI-4 → **D-2** | **Program re-select** (static review, carried from 1.0.1): clicking the already-active program may re-run the recall and discard unsaved edits, if `live.tab` re-outputs the same value. | NOT VERIFIED | No |
| OI-5 → **D-1** | **FIX APPLIED in rc3, confirm with L-7a.** **.adv preset hot-load**: root cause traced (start-up sequence re-runs on preset load with program logic enabled; `docs/validation/DEFECTS.md`). Original note: (static review, carried from 1.0.1): if Live restores the Program parameter before the 120 stored program slots, the recall may use previous slot contents. Loading a Set is not affected. | NOT VERIFIED | No (verify in L-7) |
| OI-6 | **HOLD release with TIME > ~944 ms** fades the loop out before the first new echo arrives, leaving a gap of ≤ ~79 ms (at 1023 ms). This is a design consequence of the 64K-word memory, documented in the manual. | By design | No |
| OI-7 | **Converter overload after HOLD release** at high input level with FEEDBACK > 0: the loop being regenerated into new echoes can exceed the 13-bit converter's full scale. Authentic behaviour, as on the hardware. | Informational | No |
| OI-8 | **Test tooling on Windows/macOS** (Python + C compiler) not run. The device itself has no such dependency. | NOT VERIFIED | No |
| OI-10 | **D-3:** undelayed wet signal in the first 25 ms after the device is created (pre-existing since v1.0). Fix deferred to protect the bit-identical A/B baseline. | Known, minor | No (your decision) |
| OI-11 | **RESOLVED in rc5 by LOOP COMP / CAL (confirm with L-5d).** **EXT loop latency:** each pass through the external track adds Live's routing latency (≥ one buffer + that track's device latency), so EXT repeat periods are TIME + latency. Not compensated (the amount isn't known to the device). | Documented | No |
| OI-12 | **HW-1: alias images from the clock-domain conversion** (for example a 1 kHz image 10 dB below a 17 kHz tone at 48 kHz). Not fixed in rc6; remediation candidates are on separate branches, not merged. See `docs/validation/RELEASE_DECISION.md`. | OPEN | Needs a recorded decision (see release decision) |
| OI-9 | **Interface appearance** in Live vs `docs/ui_preview.png` (rendered from the layout geometry, not by Max). | NOT VERIFIED | No |

## Resolved in v1.0.2-rc1

| Was | Resolution |
|---|---|
| v1.0.1 known limitation 4.1: HOLD release step | Fixed and tested (108-case matrix + special cases + regression audio) |
| v1.0.1 known limitation 4.2: NaN/±inf input poisons state | Fixed and tested (single, burst and alternating invalid input; during HOLD; true stereo) |
| v1.0.1 known limitation 4.3: NaN parameter values | Fixed in the C model (23 parameters); gen~ behaviour, see OI-3 |
| HOLD re-engaged within ~1 s of a release captured the old raw seam (found during rc1 testing, pre-existing in v1.0.1) | Fixed by the same change; tested against a first-ever-HOLD reference |

# Final validation — defects found and fixes applied

Change control: a defect is fixed only after it has been reproduced. Where reproduction needs Ableton Live, which was not available, the defect is documented with its evidence and a ready fix, but **not applied**.

## Summary

| ID | Severity | Area | Status | Fix applied? |
|---|---|---|---|---|
| D-1 | **High (suspected)** | `.adv` preset hot-load (and device save) overwrites program-stored controls | Root cause traced; **runtime reproduction BLOCKED** | **Yes, in rc3** on the owner's instruction, ahead of Live reproduction. Confirm with L-7a |
| UI-1 | **Critical** | Blank device panel in Live 12: only the dark backing panel was drawn | **Reproduced in Live 12 Suite (Windows) by the owner**; Max Console clean | **Yes, rc4**: static backing panels moved to Max's background layer. **Confirmed fixed in Live by the owner** |
| UI-2 | Low (cosmetic, console noise) | Max Console flooded with `parameter '<unknown>' not found` | **Reproduced in Live 12 by the owner (rc4)**; no red errors | **Yes, rc5**: the rc4 'Ext Loop' bank had 2 entries instead of 8 slots; padded with `-`. Builder and static check now enforce 8 slots. Confirm in rc5 |
| D-2 | Medium (suspected) | Re-selecting the active program (incl. M) can discard panel edits | Depends on `live.tab` re-output behaviour; **runtime reproduction BLOCKED** | No |
| D-3 | Minor | Undelayed wet signal in the first 25 ms after the device is created | **Reproduced** (C build, identical in v1.0.1 and rc1) | No: deferred (see rationale) |
| T-1 | Test tooling | CPU sanity test flaked (19× vs ≥20× threshold) on a shared 2-vCPU VM | Reproduced | **Yes**: threshold changed to a ≥5× sanity floor |

rc2: no DSP, patcher, preset or parameter change (the `.amxd` was byte-identical to rc1). **rc3:** the D-1 fix below, plus the LFO Mod-mapping feature (`CHANGELOG.md`); the DSP is unchanged.

---

## D-1 — `.adv` hot-load overwrites the restored panel with the stored program/manual snapshot

**Evidence (static, deterministic):**
1. Cycling '74 documents that `live.thisdevice` sends its bang not only when the device is loaded, but also every time a new preset is loaded or the device is saved.
2. In the shipped patcher, `live.thisdevice` (obj-166) → `[t b b b b b]` (obj-167). Outlet 2 bangs all 35 control objects, **including the Program tab (obj-379)**. Program changes pass through `[gate 1]` (obj-396), which is opened by outlet 0 (via obj-428) and **never closed again**.
3. On the first load the gate is still closed when outlet 2 fires, so there is no recall (Set reopen is safe). On every later bang, i.e. a preset hot-load or device save, the gate is open: the Program tab output runs the program logic and recalls the active slot into the 12 program-stored controls.
4. In **M (manual)** that slot is the snapshot taken the last time you *left* M. If you never left M, it holds the factory manual values.

**Predicted reproduction in Live (checklist L-7a):** new device, stay in M, set TIME 500, save an `.adv`; set TIME 200; hot-load the `.adv` onto the same device. **Expected: 500. Predicted with the defect: 380** (factory manual value), plus the other 11 program-stored controls reverting.

Parameter restore order is also documented as indeterminate for equal Order values. If the preset changes the Program value, a recall can also run *during* the restore.

**Fix applied in rc3 (owner's decision; Live reproduction still outstanding):**
1. `[t b b b b b]` outlet 3 → message `0` → the program-logic `[gate 1]`, so every re-run of the start-up sequence closes program logic before outlet 2 re-outputs Program; outlet 0 re-opens it. One cord.
2. Recall order: Program `parameter_order` 0, all other 157 parameters order 1 (Cycling '74: lower numbers are restored first). If a preset changes the program, its recall now runs *before* the panel and slot values are restored, and they win.

Regression checks: `tools/inspect_amxd.py` static check "D-1: program logic closed…" (wiring and order), and checklist L-7a in Live. Interface, DSP and parameter definitions are unchanged (`tools/check_compat.py`: only modulation mode and order differ).

**Not affected:** opening a Set, or dragging a new device/preset onto a track, provided Live initialises a fresh instance before the first bang.

**Proposed minimal fix (ready, not applied):** one patch cord from the existing `"0"` message (obj-427, fired by start-up outlet 3) to the left inlet of the program-logic gate (obj-396). Program logic is then disabled while the start-up sequence re-pushes the control values, and re-enabled by outlet 0. If L-7a still fails after this fix (recall during the parameter restore itself), the second step is to give the Program parameter a lower recall *Order* than the program-stored controls. Both changes must be verified in Live.

## D-2 — re-selecting the active program discards edits

**Evidence:** the program logic recalls the selected slot on every Program output. If clicking the already-selected `live.tab` cell outputs the index again (not confirmed in the documentation), then re-clicking **M** restores the stale manual snapshot, and re-clicking a stored program discards its temporary edits. The second may be acceptable hardware-like behaviour; the first is not.

**Predicted reproduction (L-7b):** in M set TIME 500 (never leave M); click **M** again. Defect if TIME jumps to 380.

**Proposed fix (not applied):** ignore a Program output equal to the current program (compare against `[i]` obj-395 → logic). Verify in Live.

## D-3 — start-up tap crossfade (pre-existing since v1.0)

On instantiation the two delay taps start at 0 ms and reach the set time through the normal 25 ms time-change crossfade. Audio arriving in the first 25 ms is therefore echoed almost undelayed: −10.9 dB re input in the first 50 ms of a fresh engine with BALANCE 10. It is exactly silent after 50 ms of settling. Measured identical in v1.0.1 and rc1 (test 43, reported as a known-limitation FAIL).

**Why deferred:** the fix (snap the taps to the target on the first frame) is three lines of GenExpr. However, it changes the start-up output of every render. That would invalidate the bit-identical A/B baseline against v1.0.1 (47 scenarios + 19 demos) that this release's "sound unchanged" claim rests on. The real-world effect is limited to audio already playing in the first 25 ms after the device is created (Set opening, device drop), with no click. Recommended for v1.0.3, together with an A/B baseline that uses a settled pre-roll. This is your decision; it can be applied now on request.

## T-1 — CPU test threshold (test tooling, fixed)

`t_cpu` (v1.0 suite) required ≥ 20× real-time for the C build and measured 19× while other test processes shared the 2 vCPUs. The threshold was arbitrary. It is now a ≥ 5× sanity floor, which still catches a pathological regression; the measured value is still reported. No DSP change.


---

## UI-1 — blank device panel in Live 12 (fixed in rc4)

**Reproduced** by the owner in Ableton Live 12 Suite on Windows: the device loaded at full width with its title, showing only the dark backing colour; the Max Console was empty (no errors).

**Root cause:** every panel was in Max's foreground layer, so the full-size backing panel was drawn over the controls. The static checks and the UI preview renderer assumed array order alone sets the drawing order, which doesn't hold in Live.

**Fix (smallest):** set `background` 1 on the 20 static backing panels (no cords go into them); the 43 driven panels (LEDs, segments) stay in front. **Verified** by the owner with a test build: the panel now displays.

**Regression check:** `tools/inspect_amxd.py` "UI-1: backing panels in the background layer…".

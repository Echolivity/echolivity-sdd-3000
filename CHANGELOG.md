# Changelog

## 1.0.2-rc5 — 2026-11-12 — owner's Live 12 results; triplets; LOOP COMP / CAL; console fix

### Fixed
- **UI-2 (found by the owner in Live 12):** the Max Console filled with `parameter '<unknown>' not found`. Cause: the rc4 "Ext Loop" parameter bank listed 2 parameters instead of 8 slots. Banks now always hold 8 slots (`-` = empty); the builder and `tools/inspect_amxd.py` enforce it.

### Added (owner requests)
- **Triplets in SYNC DIV:** musician labels (1/8T, 1/4T, 1/2T, 1/8D, 1/4D…; same values and indices as before) plus **1/16T** and **1/32T**, appended to the end of the menu so old Sets and programs keep their division.
- **LOOP COMP (0–250 ms) and CAL** for the external loop. CAL pauses the loop for about 0.5 s, sends one click on outputs 3/4, times its return on inputs 3/4 to the sample and writes the result into LOOP COMP. In EXT the delay is shortened by LOOP COMP, so external repeats land on TIME. The click never reaches the main outputs. Not applied in INT or BOTH; LOOP COMP 0 is bit-identical to rc4.

### Documentation (from the musical evaluation, P1/P3/P5/P6)
- Manual: input-level quick start; LFO display and TIME-lag notes; INTENSITY fine-adjust tip; controlled self-oscillation tip; stereo-from-mono note.

### Validation
- Owner, Ableton Live 12 Suite, Windows: panel and new controls show; no errors; no clicks; HOLD; program memory WRITE/recall; LFO Mod mapping accepted; external loop routing works; 8 instances without dropouts. See `docs/validation/LIVE_INTEGRATION_REPORT.md`.
- Engine tests: 51 (+4: rc4 bit-identity, triplets, CAL, LOOP COMP). Static checks: 20/20 (bank slots enforced). Compatibility: all 158 v1.0.1 parameters present; only the 11 Sync Division parameters extended (0–10 → 0–12).

## 1.0.2-rc4 addendum — 2026-11-12 — musical evaluation (no device change)

`dist/ECHOLIVITY SDD-3000.amxd`, the GenExpr, parameters and presets are byte-identical to the rc4 package.
- `tests/musical_eval.py`: renders 8 kinds of dub material and measures repeat degradation, loop filtering, transients, converter character, gain staging, self-oscillation rides, modulation movement, stereo and EXT-loop timing.
- `docs/validation/MUSICAL_EVALUATION.md` (+ `.json`): 6 ranked findings, confirmed strengths, rejected hypotheses, proposals P1–P6 (none applied).
- `audio_examples/musical_eval/`: 35 lossless FLAC renders.

## 1.0.2-rc4 — 2026-11-12 — first Ableton Live test: blank panel fixed; external regeneration loop

### Added (owner request)
- **External regeneration loop:** new **FB ROUTE** (INT / EXT / BOTH) and **RETURN** (0–10, gain RETURN/7) in REGENERATION. The device now has 4 inputs and 4 outputs: **output 3/4 = loop send** (regeneration tap after LOW/HIGH, unity, always active, safety ceiling), **input 3/4 = loop return** (NaN/inf-guarded, summed into the loop like the internal feedback). Routed with Live's own track choosers. New Push bank "Ext Loop". Manual: "External regeneration loop".
- **INT (default) is bit-identical to rc3** on all original outputs, even with noise, NaN or inf on the return inputs (test 45). CPU +~0.5 % of a core per instance (C build, 48 kHz).

### Fixed
- **UI-1 (critical, found in Live 12 Suite on Windows by the owner):** the device loaded with a clean Max Console but showed only the dark backing panel; no controls or labels were visible. The 20 static backing panels are now in Max's background layer, which is always drawn behind the foreground (Cycling '74, "Foreground and Background Layers"). The 43 panels that change colour (LEDs, 7-segment digits) stay in the foreground. **Confirmed in Live by the owner: the panel now shows.**

### Unchanged
- Sound in INT mode, existing parameters, presets, layout and colours of the existing controls. `tools/inspect_amxd.py`: 20 checks (+UI-1; audio-routing check now covers the 4-channel I/O). Engine tests: 47 (+3 for the EXT loop).

## 1.0.2-rc3 — 2026-11-12 — LFO Mod mapping + D-1 fix

Decision: CONDITIONAL PASS, not production-ready; Ableton Live validation still outstanding (`docs/validation/RELEASE_DECISION.md`).

### Added (owner request)
- **LFO / modulator "Mod" mapping** on the 13 continuous knobs (TIME, FEEDBACK, BALANCE, INPUT LEVEL, OUTPUT GAIN, INTENSITY, FREQUENCY, ENV SENS, ENV RELEASE, WIDTH, Preamp DRIVE/TONE/TRIM): `parameter_modmode` 3 (Additive). Live only allows Mod mapping on parameters with a Modulation Mode; stepped (Enum) controls cannot be modulated and still map with Mod off. Manual: "LFO and modulators".

### Fixed
- **D-1:** a preset hot-load or device save re-ran the start-up sequence with program logic enabled, recalling the active slot over the restored panel. The start-up sequence now closes program logic first (one cord), and Program is recalled before all other parameters (`parameter_order`). Applied on the owner's instruction before reproduction in Live; confirm with checklist L-7a.

### Unchanged
- GenExpr/DSP and sound (byte-identical; all engine tests give the same results), factory programs, parameter names/types/ranges/initial values, interface (`docs/ui_preview.png` byte-identical).

### Tests and tooling
- `tools/inspect_amxd.py`: 19 checks (+ Mod mapping, + D-1 wiring/order). `tools/check_compat.py`: verifies that only Modulation Mode and recall Order differ from v1.0.1. Checklist: new L-5b; L-7a now confirms the fix.

## 1.0.2-rc2 — 2026-11-12 — final validation round (no device change)

**`dist/ECHOLIVITY SDD-3000.amxd`, the GenExpr, the patcher, the presets and the sound are byte-identical to 1.0.2-rc1.** Decision: CONDITIONAL PASS, not production-ready; Ableton Live validation BLOCKED (`docs/validation/RELEASE_DECISION.md`).

### Found (documented, not fixed: see `docs/validation/DEFECTS.md`)
- D-1 (likely, high): `.adv` hot-load re-runs the start-up sequence with program logic enabled and recalls the active slot over the restored panel (stale manual snapshot in M). Root cause traced; 1-cord fix ready; needs reproduction in Live.
- D-2 (suspected, medium): re-selecting the active program can discard edits.
- D-3 (minor, pre-existing since v1.0): undelayed wet signal in the first 25 ms after the device is created.

### Changed (tests and tooling only)
- Tests 42–44: dry/wet balance law, start-up tap (documents D-3), block-size independence.
- `t_cpu` threshold changed from an arbitrary ≥20× to a ≥5× sanity floor after a load-induced flake (T-1).
- `tools/check_compat.py` (static parameter/preset compatibility); `tests/reference/ECHOLIVITY SDD-3000 v1.0.1.amxd` (comparison baseline); `tests/bench_engine.c` extended (rates × block sizes × 1/8 instances × static/automation/HOLD+FB10).
- `docs/validation/` added; checklist gains L-7a/L-7b; outstanding issues updated.

## 1.0.2-rc1 — 2026-11-12 — release candidate (DSP defect fixes)

**Interface, parameters (names, IDs, ranges), presets and features are unchanged.** For all valid audio outside HOLD release, output is bit-identical to 1.0.1 (47 A/B scenarios; all 19 demo renders re-render bit-identically). Ableton Live validation is outstanding; see `docs/LIVE_VALIDATION_CHECKLIST.md`.

### Fixed (DSP)
- **HOLD release discontinuity.** After release, the loop now keeps playing while new audio is written behind the HOLD reader. When the delay tap reads only new audio (one delay time later), the loop crossfades out over 10 ms (smoothstep). The click is gone (+27 to +35 dB click excess in v1.0.1, ≤ +1.2 dB over references in v1.0.2, across 108 cases). Above ~944 ms delay, the loop fades slightly before the first new echo (gap ≤ ~80 ms) because of the 64K-word memory. HOLD engage and HOLD while engaged are unchanged.
- **HOLD re-engaged within ~1 s of a release** no longer captures the previous loop's raw seam (a recurring click in 1.0.1).
- **Invalid input protection.** NaN/±inf input samples, and NaN parameter values in the C model, can no longer corrupt memory, feedback or filter states; recovery is immediate. Valid audio is unaffected.

### Fixed (tooling)
- `tests/render_examples.py` failed on a clean checkout (no `build/`); it now builds the engine itself. `tools/verify_release.py` now checks the renderer without a pre-built engine.

### Added
- Tests 38–41: 108-case HOLD-release matrix with special cases, HOLD re-engage, A/B regression against the 1.0.1 DSP (`tests/reference/`), latency, per-rate CPU. Tests 30, 36 and 37 (known limitations in 1.0.1) are now acceptance tests. 41/41 PASS.
- `audio_examples/regression/`: 1.0.1 vs 1.0.2 pairs. `tests/bench_engine.c`: C benchmark.
- `docs/ENGINEERING_CHANGES.md`, `docs/OUTSTANDING_ISSUES.md`, `docs/LIVE_VALIDATION_CHECKLIST.md`, `docs/measurements/`.

### Changed (documentation)
- Manual: HOLD release behaviour; the two v1.0.1 known limitations removed; robustness note.
- Research notes: HOLD release and the input guard are listed as engineering approximations.
- Output protection: input guard documented.

## 1.0.1 — 2026-11-11 — engineering hardening (maintenance release)

**Sound, presets, parameters and interface are unchanged.** `src/gen/echolivity_core.genexpr`, `presets/factory_programs.json`, `src/max/ECHOLIVITY_SDD-3000.maxpat` and `dist/ECHOLIVITY SDD-3000.amxd` are byte-identical to v1.0 (SHA-256 in `SHA256SUMS.txt`).

### Fixed
- **Clean-build defect:** `tests/run_tests.py` failed on a fresh extraction because `build/` (not shipped) did not exist (`FileNotFoundError: build/engine.c`). `tests/engine.py` now creates it. It also uses the running Python interpreter instead of a hard-coded `python3`, honours `CC`, and gives a clear message if the engine has not been built.
- **Documentation:** the demo inventory said "17 rendered audio examples"; there are 18 renders + 1 dry source = 19 WAV files.
- **Documentation:** the output "safety ceiling" was described as keeping output "below +12 dBFS". It is a soft-saturation curve with a +12.04 dBFS asymptote and is not a 0 dBFS limiter. See the new `docs/OUTPUT_PROTECTION.md`.
- **Documentation:** the research notes listed two engineering safeguards (droop compensation, safety ceiling) as "modern enhancements"; they are now classified as engineering approximations. Added a "measured characteristics" section.

### Added (tests and tooling only)
- 12 new engine tests: FEEDBACK 10 across all loop options; per-vector automation and smoothed ramps during playback; TRUE STEREO isolation; HOLD engage; HOLD release; BYPASS transitions and residual; sample-rate change without reset; memory-boundary safety; out-of-range values; huge finite input; non-finite input; NaN parameters. 37 tests in total.
- `tools/inspect_amxd.py`: 17 static checks of the device (parameters, wiring, ranges vs gen~ Params, program memory, init, tempo chain, routing, layout, byte-identical rebuild).
- `tools/analyse_output_protection.py`, `tools/verify_release.py`, `SHA256SUMS.txt`.
- Test-harness-only C entry points in `tools/gen2c.py` (`set_param_raw`, `set_samplerate`). These do not affect the GenExpr or the device.
- `tests/run_tests.py` now exits non-zero on unexpected failures.

### Known limitations found by the new tests (not fixed: DSP frozen in this release)
- **HOLD release click:** one delay time after HOLD is released, the echo switches from pre-HOLD memory to newly written audio with a step (2.8–6.9× the steady-state sample step).
- **Non-finite input:** a single NaN/±inf input sample permanently corrupts the engine state.
- Both are documented with evidence and proposed fixes in `docs/TEST_REPORT.md`, for a future release.

## 1.0.0 — 2026-11-11 — first release

### Audio engine (gen~)
- Emulates a 64K-word memory on its own 64 kHz clock. Modulation sweeps the clock (2:1), as in the original block diagram.
- 13-bit gain-ranged converter (12-bit + range bit), 50/15 µs pre/de-emphasis, 2+2-pole band-limiting (−3 dB @ 17 kHz).
- Regeneration summed before the converter. LOW (125/250/500 Hz, −3 dB/oct) and HIGH (8k/4k/2k, −6 dB/oct) filters in the loop. Feedback INV. Self-oscillation above ~7 is bounded by the converter clip.
- HOLD: ~1 s lossless loop with a seam crossfade; input locked out.
- TRI (rounded trough) / SQUARE / smoothed RND / ENV modulation, 0.1–15 Hz.
- Input stage: −30/−10/+4 attenuator, Hi-Z amp, LEVEL, op-amp clipping calibrated to the service-manual clip points. Preamp character stage with independent on/off.
- Outputs: MONO (VARIABLE), STEREO A (DIRECT/+MIX), STEREO B (+MIX/−MIX), output INV, −20/−10/+4 attenuator.
- Modern: tempo sync (11 divisions), continuous time, crossfade/glide time changes, true stereo, width, wet only, output gain, soft loop saturation, −6 dB/oct LOW option, clean converter, envelope sensitivity/release, safety ceiling.
- Per-host-rate droop compensation (44.1–192 kHz) so the 64 kHz clock emulation meets the original response spec.
- No ramps on load (smoothers start at their saved values).

### Device
- Rack-style interface: red 7-segment display with edit dot, headroom meter, LFO LED. Yellow/white legends for original functions, blue for modern ones.
- 9 programs + manual, WRITE to any slot, ▲/▼. Saved with the Set and with device presets.
- 9 factory programs, partly taken from the owner's-manual application chart.
- 38 automatable / MIDI-mappable parameters in 3 Push banks.

### Validation
- 25 automated engine tests (see `docs/TEST_REPORT.md`) plus 18 rendered audio examples (v1.0 text said 17; corrected in 1.0.1).

### Fixed during development
- HF droop of the clock emulation (−7 dB @ 17 kHz at 44.1 kHz) was corrected to −2.9 dB.
- Parameters no longer ramp up from zero on load.
- Character-off + extreme gain could reach +46 dBFS; a safety ceiling now holds +12 dBFS.
- The output-stage soft clip now bypasses with the character stage.

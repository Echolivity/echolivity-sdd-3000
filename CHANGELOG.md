# Changelog

## Unreleased — REVERSE (feature branch `feature/reverse-regen`, not merged; owner request)

### Added
- **REVERSE** menu (REGENERATION section, modern row): OFF / REV / ALT / ALT R.
  - **REV:** every repeat plays backwards; the loop itself runs forwards.
  - **ALT:** the first echo is forwards, then the direction flips on every pass (forwards, backwards, forwards…).
  - **ALT R:** the first echo is backwards, then alternating.
  - Each reversed slice is one delay time long. A reversed echo arrives between 0.5 and 1.5 × TIME depending on where the note falls in the slice, and is loudest exactly on TIME.
  - HOLD always plays its loop forwards. Switching modes crossfades over 25 ms.
  - One new Live parameter, **Reverse** (163 in total), in a new Push bank "Reverse". It is not stored in programs, so programs, presets and Sets recall as before.
- DSP: a 2 × 64K-word reverse memory records exactly what the main memory records; two Hann-windowed readers half a slice apart read it backwards, through their own D/A chain and LOW/HIGH filters. That path is only computed while a REVERSE mode is on.

### Unchanged
- **REVERSE OFF is bit-identical to rc6** on all 8 outputs (INT, EXT, BOTH, HOLD, modulation, glide/SYNC; new reference `tests/reference/echolivity_core_v1.0.2-rc6.genexpr`).
- 162/162 existing parameters, the existing Push banks and the 120 factory-program values are identical.

### Validation (offline only)
- Engine tests 56/57 (6 new REVERSE tests pass; 1 known limitation D-3, unchanged). Static checks 20/20 (expected counts updated for the new parameter). Preset compatibility vs rc6 6/6.
- **Not yet tested in Live.** HW-1 is not addressed by this branch.

## 1.0.2-rc6 — 2026-11-13 — SEND / RTN routing menus (owner request)

### Added
- **SEND and RTN menus** (PROGRAM area, under WRITE/TO): choose where the regeneration send (device outputs 3/4) goes and where the return (device inputs 3/4) comes from, from the device itself. The left menu picks the track; the right menu picks the channel or tap point (Track In; Pre FX / Post FX / Post Mixer).
  - The menus list exactly what Live offers, including return tracks, Ext. In/Out and Main as a return source.
  - They follow routing changes made anywhere in Live.
  - Implemented with a `v8.codebox` (`src/max/fb_route_chooser.js`) driving the Live Object Model's DeviceIO routing. **Requires Live 12.2+ (Max 9).**
  - The routing is Live's own state and is saved with the Set. It is not part of ECHOLIVITY presets or programs.
  - Live's track choosers keep working as before.
- The WRITE help text that sat in that space moved to the manual.

### Unchanged
- DSP: the gen~ code is byte-identical to rc5.
- Parameters: 162/162, Push banks and the 120 factory-program values are identical, so old Sets and presets load unchanged.

### Validation
- **Owner, Ableton Live 12.4.6:** all 7 checks passed.
  1. The device loads with a clean Max console.
  2. Both menus list Live's destinations and sources.
  3. The full EXT loop works from the menus (3-Audio, Track In / Post FX).
  4. The menus follow routing changes made in Live.
  5. The routing survives save, close and reopen, and plays immediately.
  6. Renaming, adding and deleting tracks update the menus.
  7. INT mode and factory programs behave as before.

  Record: `docs/validation/RC6_SEND_RTN_LIVE_TEST.md`.
- Offline: mock Live Object Model logic test `tests/max/test_fb_route_chooser.js`, 10/10. Engine tests 50/51 (unchanged; one known limitation). Static device checks 20/20. Deterministic rebuild.

## Unreleased — hardware-reference validation (no device, DSP, preset or parameter change)

- **Evidence base:** `docs/validation/HARDWARE_REFERENCE.md` contains a specification matrix from the re-read 1982 service manual (page-cited, with confidence levels and explicit UNKNOWNs), the reference-model design, a feature classification matrix (SPECIFICATION VERIFIED / DSP VERIFIED / AUDIO MEASURED / LISTENING EVALUATED / HARDWARE UNVERIFIED) and the discrepancies found.
- **Reference models:** `tests/hwref/reference_models.py`, written from the documents only, with no constants taken from the implementation.
- **Suite:** `tests/hwref/hw_validation.py` runs deterministically in about 30 s using impulse, stepped and sustained sine, log sweep, white noise, multitone, percussion and high-level stimuli. It writes `docs/validation/HARDWARE_VALIDATION.{json,md}` and adds section 10 to `docs/TEST_REPORT.md`. Result: 28 consistent, 5 inconsistent, 8 reported, 1 not comparable.
- **Discrepancies found (not fixed; each needs an approved DSP task):**
  - **HW-1:** in-band alias images from the 64 kHz clock emulation; total distortion + noise is 0.28 % against 0.03 % typical.
  - **HW-2:** the HIGH cut uses a bilinear filter at the host rate, so it falls 3 dB further than an analog first-order filter at 16 kHz for the 8 kHz setting.
  - **HW-3:** −3.34 dB at 17 kHz at a 48 kHz host, against a −3 dB limit.
  - **HW-4:** no analog noise floor (by design).
- **Optional physical measurement:** `tools/loopback_measure.py` and `docs/validation/HARDWARE_MEASUREMENT.md` cover the interface loopback workflow and a secondary-reference procedure for commercial emulations. The analysis is self-tested in the suite. It hasn't been run on real equipment yet.
- The existing engine tests, static checks and their expected results are unchanged.

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

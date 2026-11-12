# Hardware-reference validation: method, evidence and status

This document says, for each characteristic of the 1982 Korg SDD-3000 that ECHOLIVITY reproduces:
- what the original documentation states,
- how sure we are of that statement,
- what the software does,
- how that was checked,
- what can't be known without an original unit.

**No original SDD-3000 was available.** Nothing in this repository is verified against hardware, and nothing here claims equivalence to an original unit.

Related files:
- `tests/hwref/reference_models.py`: the independent reference models.
- `tests/hwref/hw_validation.py`: the automated suite.
- `docs/validation/HARDWARE_VALIDATION.md`: the generated results table.
- `docs/validation/HARDWARE_MEASUREMENT.md`: the optional interface and plug-in measurement workflow.
- `docs/RESEARCH_NOTES.md`: the older narrative notes, still valid.

## 1. Classification vocabulary

Each feature can carry several of these at once, and each needs evidence.

| Classification | Meaning | Typical evidence |
|---|---|---|
| **SPECIFICATION VERIFIED** | The hardware behaviour is stated in a primary source that was read for this round (page cited) | Service manual scan page |
| **DSP VERIFIED** | The source code implements the documented behaviour, and an automated engine test confirms it | `tools/make_gen.py` location + `tests/run_tests.py` test |
| **AUDIO MEASURED** | Measured from rendered audio against an *independent* reference, with a tolerance derived from the documentation | `tests/hwref/hw_validation.py` result |
| **LISTENING EVALUATED** | A person listened and reported a result | Owner's Live 12 tests (`LIVE_INTEGRATION_REPORT.md`) |
| **HARDWARE UNVERIFIED** | Not compared with an original unit. **This applies to every feature** | — |

"AUDIO MEASURED" in this round means the **C build of the exact gen~ code** (`tests/engine.py`), not Ableton Live. Measuring the device inside Live through an interface is a separate, optional workflow (`HARDWARE_MEASUREMENT.md`), and it hasn't been run yet.

## 2. Sources

| Code | Source | How used this round |
|---|---|---|
| **SM** | Korg SDD-3000 Service Manual (Keio, 1982), scan provided by the owner (21 PDF pages) | **Re-read for this round.** Manual p.1 spec sheet = PDF p.3; check & adjustment manual p.15 = PDF p.17 |
| OM | SDD-3000 Owner's Manual (archive.org OCR) | Not re-read this round; cited from `RESEARCH_NOTES.md` |
| EMM | *Electronics & Music Maker*, May 1983 review | Not re-read this round; secondary |
| PARTS | syntaur.com parts list | Secondary (12-bit DAC, op-amp types) |
| PED | Korg SDD-3000 **pedal** (2013) MIDI implementation | **Not used as a reference for the rack unit.** The pedal is a different, digital product; it only corroborates filter frequencies and division names |
| UAD | Universal Audio plug-in manual | Third-party emulation; never ground truth |

Confidence levels:
- **High:** printed in the SM and read directly.
- **Medium:** single secondary source, or derived from SM figures by arithmetic.
- **Low:** inferred.
- **UNKNOWN:** not documented anywhere available.

## 3. Hardware specification matrix

| Area | Documented specification | Source | Confidence |
|---|---|---|---|
| Delay range / resolution | 0–1023 ms, 1 ms steps, "with full bandwidth" | SM p.1 (PDF p.3) | High |
| Memory clock | 64 kHz ± 2 kHz at INTENSITY 0 | SM p.15 §5 (PDF p.17) | High |
| Memory size | 64K words (1023 ms × 64 kHz = 65 472) | SM reference data (via RESEARCH_NOTES) | Medium |
| Modulation architecture | LFO → VCO; the clock is modulated, not a read pointer | SM p.3 block diagram (via RESEARCH_NOTES) | Medium (diagram not re-read) |
| Modulated clock | INT 10, FREQ 0, square: max 78 ± 2 kHz, min 40 ± 1 kHz (ratio ≈ 1.95) | SM p.15 §6 (PDF p.17) | High |
| Modulation | VCO 0.1–15 Hz; triangle, square, random, envelope; intensity 0–2:1 | SM p.1 | High |
| Knob law between the FREQUENCY endpoints | not documented | — | **UNKNOWN** |
| Converter | 12-bit DAC + gain ranging ("12-bit plus one") | PARTS, EMM | Medium |
| Gain-ranging threshold and switching dynamics | not documented | — | **UNKNOWN** |
| Pre-/de-emphasis | present (block diagram); values not given | SM p.3 | Medium (presence) / **UNKNOWN** (values) |
| Effect bandwidth | 20 Hz–17 kHz, +0.5 / −3 dB | SM p.1 | High |
| Direct bandwidth | 20 Hz–20 kHz ± 0.5 dB | SM p.1 | High |
| Dynamic range (A-wtd) | 94 dB effect, 110 dB direct | SM p.1 | High (value) / **UNKNOWN** (reference level, bandwidth) |
| S/N (A-wtd) | 88 dB effect, 95 dB direct | SM p.1 | High (value) / **UNKNOWN** (reference level) |
| Total distortion | 0.03 % typical at 1 kHz (effect), 0.005 % (direct) | SM p.1 | High (value) / **UNKNOWN** (level, bandwidth) |
| Input stage | −30 / −10 / +4 dBm ranges; 470 k / 47 k / 10 k; clip −13 / +7 / +21 dBm at LEVEL 5 | SM p.1 | High |
| Output stage | −20 / −10 / +4 dBm ranges; clip −3 / +7 / +21 dBm | SM p.1 | High |
| Feedback filters | LOW 125 / 250 / 500 Hz −3 dB/oct; HIGH 8k / 4k / 2k −6 dB/oct ("turn over freq", "roll off") | SM p.1 | High (as printed) / **UNKNOWN** (whether −3 dB/oct is a misprint; corner definition) |
| Filter position | after the memory, inside the regeneration path | SM p.3 (via RESEARCH_NOTES) | Medium |
| Feedback behaviour | FB 10, 50 ms, LOW 500 / HIGH 2k: oscillates after a 100 ms pulse; no oscillation without input; INV inverts phase | SM p.15 §7 (PDF p.17) | High |
| Feedback law | "above about 7 causes oscillation" → gain = FB/7 | OM | Low (inference) |
| Outputs | DIRECT, +MIX, −MIX, VARIABLE; STEREO A = DIRECT/+MIX, STEREO B = +MIX/−MIX | OM, SM p.3 | Medium |
| HOLD | loops the last ~1 s indefinitely; input locked out | OM, EMM | Medium |
| Clipping character (op-amp curves, converter overload shape) | not documented | — | **UNKNOWN** |
| Analog noise floor, hum, DRAM artefacts | only the S/N figures above | SM p.1 | **UNKNOWN** in detail |

## 4. Reference-model design

The models in `tests/hwref/reference_models.py` are written from the documents above. They import nothing from the implementation: no coefficients, curves or constants. Where documents are silent, the model returns UNKNOWN and the suite *reports* the number instead of judging it.

| Model | Derivation | Tolerance used | Why that tolerance |
|---|---|---|---|
| Delay timing | integer ms on a 64 kHz clock | ± 15.6 µs | one hardware clock period |
| Effect / direct response | SM masks | the masks themselves | SM figures |
| HIGH cut | analog first-order low-pass, −3 dB at the stated frequency | ± 0.5 dB, fc/4 to 2fc | measurement repeatability; corner definition assumed |
| LOW cut | asymptotic slope 3 dB/oct; level at turnover −1.5 to −3.5 dB | ± 0.5 dB/oct | turnover definition UNKNOWN |
| Filters inside the loop | k passes → k × single-pass attenuation | ± 0.3 dB per repeat | from the block diagram |
| Feedback decay | 20·log10(FB/7) per repeat at 1 kHz | ± 0.25 dB | law is an inference (Low) |
| Modulation | rate endpoints 0.1 / 15 Hz; depth 2:1 at INT 10; square ratio from SM §6 | ± 2 % rate, ± 0.01 ratio, SM tolerance band | SM figures |
| Quantisation | textbook 12-bit + one range bit (step 6 dB) | 5–7.5 dB step | threshold UNKNOWN |
| Gain structure | pads derived from SM clip levels (−24 / −14 dB out; +34 / +14 dB in) | ± 0.1 / ± 0.5 dB | arithmetic on SM values |
| Distortion / dynamic range | SM figures | 3 × "typical"; ± 4 dB DR | SM gives typical values without a level or bandwidth |
| Output identities | (+MIX) + (−MIX) = 2 × DIRECT | −80 dB residual | exact algebra from OM |

**Method notes found while building the suite:**
- **The emulation isn't LTI.** Running a 64 kHz memory clock inside a 44.1 / 48 / 96 kHz host makes the system non-time-invariant: it creates alias components (§6, HW-1). Multitone, noise and sweep estimates are therefore biased near the top of the band. The suite's primary response method is a **stepped sine**, one tone per render, and the broadband methods are reported only as cross-checks.
- **Stimulus levels.** Transfer measurements run 20 dB below nominal, because the pre-emphasis lifts broadband HF by up to ~10 dB, which would reach the converter's overload point.
- **Modulation depth.** It is measured with a click train (each click's echo time = the delay at that moment). Cross-correlation of noise fails while the delay moves, because the audio is time-scaled.

## 5. Results (this round, C build at 48 kHz unless stated)

**Summary:** 28 consistent with the documentation, 5 inconsistent, 8 reported without a documented reference, 1 not comparable. The full table is in `HARDWARE_VALIDATION.md`.

| Area | Measured | Documentation | Verdict |
|---|---|---|---|
| Delay 1–1023 ms | error 0.00 µs (impulse); 333.002 ms with a percussive transient | integer ms, ± 15.6 µs | CONSISTENT |
| 1 ms step | 100.4 → 100.000 ms | 1 ms step | CONSISTENT |
| Effect response, 44.1 kHz host | −2.96 … +0.09 dB, 20 Hz–17 kHz | +0.5 / −3 dB | CONSISTENT |
| Effect response, 48 kHz host | **−3.34 dB at 17 kHz**; non-monotonic at 16 kHz (−1.50 dB) | +0.5 / −3 dB | **INCONSISTENT** (HW-3) |
| Effect response, 96 kHz host | **−3.08 dB at 17 kHz** | +0.5 / −3 dB | **INCONSISTENT** (HW-3) |
| Direct response (PRE off) | ± 0.000 dB | ± 0.5 dB | CONSISTENT |
| HIGH 2 kHz | −3.01 dB at fc; −7.11 dB at 2fc (model −6.99) | 1st order | CONSISTENT |
| HIGH 4 kHz | −3.01 dB at fc; **−7.51 dB** at 8 kHz | 1st order (−6.99) | **INCONSISTENT** (HW-2, 0.53 dB) |
| HIGH 8 kHz | −3.01 dB at fc; **−10.00 dB** at 16 kHz | 1st order (−6.99) | **INCONSISTENT** (HW-2, 3.0 dB) |
| LOW 125 / 250 / 500 Hz | 2.94 dB/oct; −2.97 dB at turnover | −3 dB/oct | CONSISTENT |
| Filters per repeat (HIGH 4k) | −3.01 / −6.04 / −9.07 / −12.11 dB | k × −3.01 | CONSISTENT |
| Feedback decay | within 0.1 dB of FB/7 at 2–7 | FB/7 (inference) | CONSISTENT |
| SM check 7 | sustains at −18 dBFS; silent without input | oscillates; silent | CONSISTENT |
| Depth INT 10 (TRI) | 201.1–399.0 ms (ratio 0.504) | 2:1 | CONSISTENT |
| SQUARE INT 10 | 400 / 200 ms (2.000) | SM clock ratio 1.85–2.05 | CONSISTENT |
| Rate endpoints | 0.100 / 15.000 Hz | 0.1 / 15 Hz | CONSISTENT |
| Input clip points | −13.25 / +6.75 / +20.75 dBm (1 dB compression) | −13 / +7 / +21 dBm | CONSISTENT |
| Input / output range pads | +34 / +14 dB; −24 / −14 dB | derived from SM | CONSISTENT |
| THD (harmonics), 1 kHz | effect 0.0041 %, direct 0.0008 % | 0.03 % / 0.005 % typical | CONSISTENT |
| **Total distortion + noise, 1 kHz, effect** | **0.28 %** | 0.03 % typical | **INCONSISTENT** (HW-1) |
| Dynamic range, effect (A-wtd) | 91.5 dB re converter overload | 94 dB | CONSISTENT (± 4 dB; reference level UNKNOWN) |
| Gain-ranging step | converter error falls 7.2 dB from the top to below the range threshold | ~6 dB (one bit) | CONSISTENT |
| S/N (idle) | digital silence | 88 / 95 dB | NOT COMPARABLE (analog noise not modelled) |
| STEREO B identity | residual −92 dB | exact | CONSISTENT |
| Alias spurs (single tones, CLEAN, −20 dB) | e.g. 48 kHz host: 15 kHz → −13.6 dB at 1 kHz; 17 kHz → −10.2 dB at 1 kHz; 10 kHz → −27.5 dB at 6 kHz. 44.1 kHz host: 1 kHz → −56 dB at 18.9 kHz | none in-band on the hardware | REPORTED (HW-1) |
| Loopback analysis self-test | latency exact; response within 0.16 dB | — | CONSISTENT (method check) |

## 6. Discrepancies found

None of these has been fixed in this round. DSP changes need a separate, approved task.

- **HW-1 (significant): in-band alias images from the clock-domain conversion.**
  - **What:** a single high-frequency tone produces inharmonic components inside the audio band, measured on the C build of the exact gen~ code. For example, at a 48 kHz host a 17 kHz tone creates a 1 kHz component only 10 dB below it.
  - **Effect on the spec:** at 1 kHz the images raise "total distortion + noise" to 0.28 %, about ten times the SM's 0.03 % typical. Harmonic THD alone (0.004 %) meets the spec.
  - **Why it isn't authentic:** on the hardware, the 64 kHz images lie above 32 kHz and are removed by the analog reconstruction filter.
  - **Root cause (likely):** the reconstruction from the 64 kHz domain to the host rate (ZOH-integrated DAC with linear interpolation, then 2-pole filtering) doesn't suppress images near the host Nyquist frequency.
  - **Musical relevance:** cymbals, hats and bright transients can gain faint inharmonic content in the echoes. **Not yet evaluated by listening.**
  - **Proposed:** test a properly band-limited resampler, such as a windowed-sinc or polyphase FIR, in the 64 kHz → host path. The audible change would have to be evaluated, and the A/B baselines would need re-approval.
  - **This is the most important finding of the round.** The existing engine suite (`tests/run_tests.py`) measures only the fundamental, so it couldn't detect this.
- **HW-2 (minor): the HIGH cut deviates from an analog first-order filter above its corner.**
  - **What:** 8 kHz measures −10.0 dB at 16 kHz instead of −7.0 dB; 4 kHz measures −7.5 dB at 8 kHz instead of −7.0 dB.
  - **Root cause (confirmed in code):** the HIGH cut is a bilinear (TPT) first-order filter running at the **host** sample rate (`tools/make_gen.py`, `g_hc = tan(π·fc/sr)`; the filter itself is applied at the line marked "HIGH cut: first-order"). Its frequency warping gives exactly the measured values: at 48 kHz, 1/(1 + (tan(π·16/48)/tan(π·8/48))²) = −10.0 dB. The deviation is larger at 44.1 kHz and smaller at 96 kHz.
  - **Effect:** the corner frequency is exact, but the 8 kHz setting removes more of the 12–17 kHz octave than an RC filter would. Audible relevance is small.
  - **Proposed:** a matched-magnitude or oversampled first-order filter, needing approval.
- **HW-3 (marginal): the effect response at 17 kHz is −3.34 dB at 48 kHz and −3.08 dB at 96 kHz,** against a −3 dB limit.
  - The 44.1 kHz host meets it (−2.96 dB).
  - At 48 kHz the response is also non-monotonic around 16 kHz, where an alias image of the tone lands on itself.
  - The existing engine test, which uses a different method, reports −2.86 dB at 17 kHz. The disagreement between methods is part of the finding: the top-octave response depends on the alias interference in HW-1.
- **HW-4 (by design): no analog noise floor.** The hardware's S/N figures can't be compared. This is documented as "not modelled" in RESEARCH_NOTES §D.
- **Reported, no reference:**
  - the FREQUENCY knob law;
  - the converter overload point (+9 dBm, 5 dB above nominal: the HEADROOM meter's red +3 dB marks its onset, per the musical evaluation);
  - TRUE ST separation (a modern mode);
  - click-free transitions (a project requirement; the hardware likely clicked);
  - the output safety ceiling (a software safeguard).

## 7. Feature classification matrix

SV = SPECIFICATION VERIFIED, DV = DSP VERIFIED, AM = AUDIO MEASURED (C build), LE = LISTENING EVALUATED, HU = HARDWARE UNVERIFIED.

| Feature | SV | DV | AM | LE | HU | Evidence |
|---|---|---|---|---|---|---|
| Delay 0–1023 ms, 1 ms steps | ✓ SM p.1 | ✓ `t_delay_accuracy`, `t_ms_stepping` | ✓ consistent | partial (owner: echoes heard) | ✓ | §5 rows 1–2 |
| Continuous time, GLIDE, XFADE (modern) | n/a | ✓ `t_clicks` | — | ✓ owner: no clicks (L-2) | ✓ | `LIVE_INTEGRATION_REPORT.md` |
| Tempo sync incl. triplets (modern) | n/a | ✓ `t_sync`, `t_triplets` | — | — | ✓ | engine tests |
| Memory clock 64 kHz | ✓ SM p.15 §5 | ✓ code | indirect (timing exact) | — | ✓ | §3 |
| Clock modulation: depth 2:1, rate 0.1–15 Hz | ✓ SM p.1, p.15 §6 | ✓ `t_mod_depth`, `t_lfo_rate` | ✓ consistent | — | ✓ | §5 |
| Waveform shapes TRI / SQR / RND / ENV | ✓ (names) / Low (shapes) | ✓ `t_mod_shapes`, `t_envelope` | reported | — | ✓ | SM Fig.3/4 are sketches |
| Feedback law FB/7 | Low (OM inference) | ✓ `t_feedback_decay` | ✓ consistent | — | ✓ | §5 |
| Self-oscillation (SM check 7) | ✓ SM p.15 §7 | ✓ `t_service_manual_feedback` | ✓ consistent | — | ✓ | §5 |
| Regeneration INV | ✓ SM p.15 §7.5 | ✓ `t_feedback_extreme` | — | — | ✓ | — |
| HOLD | Medium (OM/EMM) | ✓ HOLD tests | — | ✓ owner (L-9) | ✓ | — |
| LOW cut −3 dB/oct | ✓ SM p.1 (misprint possible) | ✓ `t_filters_static` | ✓ consistent | — | ✓ | §5 |
| HIGH cut −6 dB/oct | ✓ SM p.1 | ✓ `t_filters_static` | **✗ HW-2** above fc | — | ✓ | §6 |
| Filters inside the loop | Medium (SM p.3) | ✓ `t_filters_in_loop` | ✓ consistent | — | ✓ | §5 |
| Effect bandwidth 20 Hz–17 kHz | ✓ SM p.1 | ✓ `t_wet_gain_and_response` | **marginal ✗ HW-3** at 48 / 96 kHz | — | ✓ | §6 |
| 13-bit gain-ranged converter | Medium | ✓ `t_converter` | ✓ 6 dB step; DR 91.5 dB | — | ✓ | §5 |
| Pre-/de-emphasis (50 / 15 µs assumed) | presence Medium, values UNKNOWN | ✓ code | — | — | ✓ | RESEARCH_NOTES §B |
| Distortion | ✓ SM p.1 | — | THD ✓; **total ✗ HW-1** | — | ✓ | §6 |
| Noise floor | ✓ SM p.1 | n/a (not modelled) | not comparable | — | ✓ | HW-4 |
| Input ranges and clip points | ✓ SM p.1 | ✓ `t_preamp` | ✓ consistent | — | ✓ | §5 |
| Output ranges | ✓ SM p.1 | ✓ code | ✓ consistent | — | ✓ | §5 |
| Preamp character, DRIVE / TONE / TRIM / COMP | clip points only | partial (`t_preamp`) | — | — | ✓ | approximation (RESEARCH_NOTES §B) |
| Clipping / overload curves | **UNKNOWN** | approximation | reported | — | ✓ | §6 |
| Outputs: MONO / STEREO A / B | Medium (OM) | ✓ `t_stereo_modes` | ✓ STEREO B identity | — | ✓ | §5 |
| TRUE ST, WIDTH (modern) | n/a | ✓ `t_stereo_isolation` | reported | — | ✓ | — |
| External loop, CAL, LOOP COMP (modern) | n/a | ✓ `t_fbroute_*`, `t_loop_cal`, `t_loop_comp` (simulated loop) | — | ✓ owner: routing heard; CAL not yet | ✓ | — |
| Programs / WRITE | Medium (OM) | ✓ static (`check_compat`) | n/a | ✓ owner (L-7) | ✓ | — |
| Output safety ceiling (software) | n/a | ✓ `t_fuzz`, `t_invalid_values` | reported | — | ✓ | `OUTPUT_PROTECTION.md` |

## 8. Proposed work vs completed work

**Completed in this round (version-controlled, reproducible):**
- Re-read of the SM spec sheet and check & adjustment pages, with page citations.
- The reference models, `tests/hwref/reference_models.py`.
- The suite, `tests/hwref/hw_validation.py`, covering all eight signal types:
  - impulse
  - sine (stepped and sustained)
  - log sweep
  - white noise
  - multitone
  - transient percussion
  - sustained tones
  - high-level sines
- A deterministic run of about 30 s, written to `HARDWARE_VALIDATION.{json,md}`.
- The interface and plug-in measurement tool `tools/loopback_measure.py`, with its own self-test in the suite.
- The workflow document `HARDWARE_MEASUREMENT.md`.
- A new section 10 in `TEST_REPORT.md` and a summary row there.

**Proposed, not done:**
1. Run `HARDWARE_MEASUREMENT.md` on the owner's interface to measure the device **inside Live**, so the "AUDIO MEASURED" column covers the real host.
2. Investigate HW-1, the resampler, as a separate approved DSP task with listening and re-baselining.
3. Decide on HW-2: keep the bilinear HIGH filter, or match the analog magnitude.
4. Re-read the OM and the SM block diagram (p.3) page by page, to upgrade the Medium rows.
5. An optional comparison against a commercial emulation, as a secondary reference only (procedure in `HARDWARE_MEASUREMENT.md` §4).
6. If an original unit ever becomes available, run the same stimulus through it with `tools/loopback_measure.py`. That is the only path to removing "HARDWARE UNVERIFIED".

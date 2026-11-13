# HW-1 Root-Cause Investigation — Clock-Domain Conversion Spurs

Baseline: `dfd851bef49ed81f9aac37edc25a4702f9ba7ed7` (v1.0.2-rc5 + hardware-reference validation).
> **Update (remediation phase):** the recommendation below (candidate B) has been superseded. Candidate B fails the TIME-0 latency and timing contracts. The remediation architecture is **candidate D**: continuous-time analog-prototype conversion with a TIME-0 error-feedforward path. See `HW1_ARCHITECTURE_DECISION.md` and `HW1_REMEDIATION_REPORT.md` (recommendation: request further investigation, because native validation is still pending). HW-1 remains open.

Status: **investigation and recommendation only.** The production DSP, the device interface, the presets and the downloadable device are unchanged. HW-1 is **not fixed**, and the release status is unchanged.

All numbers below were measured in this repository with the C-compiled engine (`tools/gen2c.py`) or the isolated numpy model in `experiments/hw1/`. Nothing here was measured on real hardware or inside Live/Max.

---

## 1. Confirmed root cause

HW-1 is caused by **imaging in the two clock-domain conversions** around the emulated 64 kHz memory clock, which is not a multiple of the host rate. It is not caused by converter nonlinearity or by I/O harmonic distortion.

1. **Host → memory (input side).** The input is linearly interpolated between host samples (`xi = xp + (xc − xp)·tt`). Linear interpolation is a triangle kernel. Its spectrum is sinc²(f/fs_h), which only partly suppresses the host-rate images at k·fs_h ± f. Sampling at fv = 64 kHz folds those images back into the audio band:
   - 48 kHz host, 17 kHz tone: the image at 48 + 17 = 65 kHz folds to |65 − 64| = **1 kHz**, and the image at 96 − 17 = 79 kHz folds to |79 − 64| = **15 kHz**.
2. **Memory → host (output side).** The DAC zero-order hold is integrated over each host sample, which gives a box average. Its response is sinc(f/64k)·sinc(f/fs_h). That leaves the 64 kHz images at 64k ± f, which fold at the host rate:
   - 44.1 kHz host, 1 kHz tone: 64 − 1 = 63 kHz folds to 63 − 44.1 = **18.9 kHz**.
   - 44.1 kHz host, 17 kHz tone: 64 − 17 = 47 kHz folds to **2.9 kHz**.
   - 96 kHz host: 64 − 17 = 47 kHz is passed through as a real ultrasonic image.
3. **Aggravating factor: de-emphasis.** De-emphasis sits after the conversion. It attenuates the wanted HF tone by up to about 10 dB while leaving the LF spurs alone, which worsens the spur-to-tone ratio by about 7–10 dB. In the isolated model without emphasis, the 1 kHz spur is −17.8 dB; in the device it is −10.2 dB.
4. **Self-interference.** When the image lands on the tone itself, it beats with it. Examples at a 48 kHz host: 8 kHz (64 − 7·8 = 8) and 16 kHz (64 − 3·16 = 16). This explains the non-monotonic effect response reported as HW-3.
5. **Feedback** recirculates the spurs through the conversion on every repeat. At 48 kHz, 17 kHz, FB 5 @ 50 ms, the 1 kHz component reaches −1.6 dB re the tone.

Evidence that it is linear but not time-invariant, rather than nonlinear:
- The spur level relative to the tone is independent of input level (−40 to −20 dB re nominal), of TIME, of 13-bit mode and of PRE.
- The spurs are absent on the direct (dry) path.
- The spur frequencies follow |k·fs_h ± f − m·64k|, not harmonic series.
- The spurs fall away when the interpolation and reconstruction kernels are replaced by band-limited ones, while the quantiser is kept (§4).

Attribution in the isolated model (48 kHz, 17 kHz → 1 kHz spur, quantiser on):

| Configuration | 1 kHz spur |
|---|---|
| Production (linear in, ZOH-box out) | −17.8 dB |
| Band-limited input only | −36 dB |
| Band-limited output only | −19.6 dB |
| Both band-limited (16 taps) | −34 dB |
| Both band-limited (32 taps / 20 kHz) | −127 dB |

The input interpolation dominates at 48 kHz. The output side dominates at 44.1 kHz for low tones (1 kHz case: output −49 dB vs input −70 dB) and creates the 47 kHz image at 96 kHz.

## 2. Reproduction results (production engine)

Conditions: CLEAN, PRE off, −20 dB re nominal; values in dB relative to the wanted tone. Source: `experiments/hw1/results/reproduction.json`.

| Host | Tone | Spurs |
|---|---|---|
| 48 kHz | 17 kHz | **1 kHz −10.2**, 15 kHz −13.4 |
| 48 kHz | 15 kHz | **1 kHz −13.6**, 17 kHz −15.7 |
| 44.1 kHz | 1 kHz | **18.9 kHz −56.4** |
| 44.1 kHz | 17 kHz | **2.9 kHz −16.6**, 7.2 kHz −17.8 |
| 96 kHz | 17 kHz | 15 kHz −18.5, 47 kHz −70 |

All four reported cases reproduce.

Worst spur against tone frequency at 48 kHz:

| Tone | Worst spur |
|---|---|
| 100 Hz | −74 dB |
| 1 kHz | −53 dB |
| 10 kHz | −27.5 dB |
| 20 kHz | −8.4 dB |

The full sweeps (100 Hz–20 kHz at 44.1, 48 and 96 kHz) are in the JSON and in `spurs_vs_frequency.png`.

Conditions tested:
- direct path vs delayed path;
- FB 0 vs 5;
- modulation off vs INT;
- three input levels;
- HF comp on vs off;
- 13-bit and PRE settings.

At nominal level, converter-overload distortion (a separate, authentic nonlinear class) adds on top of the spurs.

## 3. Explanation of the clock-domain conversion problem

Let fs_h be the host rate and fv = 64 kHz the memory clock.

**Input side.** The production tick loop evaluates the input at the fractional host time t = n + τ. Linear interpolation of x[n] is the convolution of the impulse train with a triangle of width 2/fs_h. Its transfer function is

  H_in(f) = sinc²(f / fs_h).

Images of a tone at f exist at k·fs_h ± f with relative level H_in(k·fs_h ± f) / H_in(f). For 48 kHz and f = 17 kHz:

  H_in(65 kHz) = sinc²(1.354) ≈ −27 dB, against H_in(17 kHz) ≈ −3.8 dB,

so the image is only about 23 dB below the tone before any emphasis effect. These images are then sampled at fv and fold to |k·fs_h ± f − m·fv|.

**Output side.** The memory samples are held (ZOH, sinc(f/fv)) and integrated over each host period (sinc(f/fs_h)). Images at m·fv ± f pass with

  H_out(f) = sinc(f/fv) · sinc(f/fs_h),

and are then sampled at fs_h, which folds them to |m·fv ± f − k·fs_h|.

**Why the spurs are level-independent but move with frequency.** Both kernels are linear, but their image attenuation depends on f. That is why the spurs grow by roughly 6 dB per octave towards the top. Because fv/fs_h is irrational in practice (64/44.1) or non-integer (64/48 = 4/3), the folded products are not harmonically related and are audible as inharmonic tones. They are not hiss.

**Emphasis interaction.** The device's pre-/de-emphasis pair is applied around the conversion. Pre-emphasis raises the tone before the images are created, but the images fold to LF, where de-emphasis gives no attenuation, while the HF tone is cut back down by de-emphasis. That is a net loss of the ratio.

**Not the cause:**
- The 12-bit quantiser and range bit produce an error floor of about −72 dB re the tone in all variants.
- Harmonic distortion at the reference level is about −88 dB (THD 0.0041 %).
- The droop EQ only shapes the result.

## 4. Candidate solutions and trade-offs

All three keep the 64 kHz memory clock, the quantiser, gain ranging and emphasis. Only the two conversion kernels change. Model numbers come from `results/candidates.json` and `results/taps_tradeoff.json`.

| | Production | A: Catmull-Rom in + FOH box out | B: band-limited windowed sinc both ways | C: ×4 polyphase oversampling around the core |
|---|---|---|---|---|
| Worst spur 44.1 / 48 / 96 kHz | −17.6 / −11.9 / −8.2 dB | −28.7 / −22.7 / −16.4 | **−115 / −118 / −106** | −35 / −109 / −8.7 (44 kHz ultrasonic) |
| Spur spill with modulated 17 kHz tone | −16 dB | −28 | **−128** | −37 |
| Core passband at 17 kHz / 48 kHz (before EQ) | −5.33 dB | −5.23 | −0.54 (32 taps) | −0.92 |
| Added latency | 0 | 0 | kernel/2 (0.25–0.73 ms) | filter group delay (~0.5 ms) |
| MACs per host sample per channel | ~5 | ~30 | ~256 (32 taps); scales with taps | ~77 |
| Memory | — | none | kernel table ~16 k floats + rings 128×2, 256×4 | polyphase states |
| gen~ / Max 9 | — | trivial | uses Data, while, peek/poke; compiles via the gen2c subset; **not verified in Max** | needs an oversampled sub-loop; awkward in gen~ |
| Modulated clock | — | works | works natively: kernels are evaluated at exact continuous tick times | works |
| Delay accuracy | exact | exact | exact after latency compensation (see TIME 0 risk) | exact + fixed offset |
| HOLD / feedback | — | unchanged | HOLD release timing must account for latency; more top-octave loop gain | similar to B |

Conclusions:
- **A** is cheap but buys only about 11 dB. The spurs stay clearly audible (−23 dB at 48 kHz / 17 kHz).
- **C** fixes 48 kHz but not 44.1 kHz or 96 kHz, because the ×4 grid is still incommensurate with 64 kHz.
- **B** is the only approach that removes the mechanism at every host rate and under modulation.

Taps trade-off for B (fc 20 kHz, 48 kHz host):

| Taps | Worst spur | Response at 15 / 17 kHz | Latency |
|---|---|---|---|
| 12 | −104 dB | −2.36 dB at 15 kHz | 0.25 ms |
| 16 | −110 dB | −1.11 / −3.49 dB | 0.33 ms |
| 24 | −120 dB | −0.14 / −1.53 dB | 0.50 ms |
| 32 | −127 dB | 0 / −0.54 dB | 0.67 ms |

Taps must scale with sr so that the kernel has a fixed duration. At 96 kHz, a fixed 32 taps behaves like 16 taps at 48 kHz.

## 5. Recommended solution

**Candidate B**: band-limited windowed-sinc (Blackman-Harris) kernels in continuous host time for both conversion directions.
- **Input side:** for each memory tick, evaluate the input at the tick's exact host time, delayed by kernel/2, using a precomputed 128-points-per-sample kernel table.
- **Output side:** distribute each held DAC value onto the host grid with the same kernel, y[n] = Σ q_k·hold_k·h(n − D − t_k), normalised.

Use a **fixed kernel duration** (experiment: 0.5 ms, i.e. 24 taps at 48 kHz) with fc ≈ 20 kHz (19 kHz at 44.1 kHz). Compensate the latency in the delay-time target so that echo times stay exact.

The recommendation is conditional on the following open items, which must be resolved before any production change is proposed:
1. **TIME 0 latency.** The minimum wet delay rises from 0.02 ms to 0.50 ms. Mixed with dry at TIME 0, this forms a comb with its first notch at about 1 kHz. Options to evaluate (none tested):
   - a shorter (12–16 tap) kernel;
   - a minimum-phase kernel;
   - a short-kernel path only at TIME < 1 ms.
2. **HOLD release timing.** The latency compensation shifted the HOLD release logic (worst early deviation 0.396 ms). The release logic needs the same offset.
3. **Top-octave voicing.**
   - The production droop/HF-comp EQ was disabled in the experiment because B has no droop. Programs with FLAT/high HIGH settings are up to +2.6 dB brighter at 10–16 kHz.
   - The HIGH 8 kHz filter's bilinear warping (HW-2) is now exposed: −10.0 dB at 2·fc vs −8.38 dB in production.
   - Decide whether to re-voice the HIGH filters (fix HW-2) or keep a fixed gentle top-octave tilt to preserve the current character.
4. **Behaviour regressions found in the existing suite:**
   - INV click (3.05× vs limit);
   - FB 6.8 @ 8 ms decay (−76 vs −81 dBFS required);
   - FB 10 wet peak (−13.4 vs −13 dBFS bound);
   - NaN-storm recovery (8.1 dB deviation vs 0.32 dB).

   The first three are consistent with more top-octave loop gain once the droop is removed. The NaN case is likely the kernel rings holding non-finite values and needs a ring flush on the existing NaN guard.
5. **Verify in Max 9 / Live 12:** compile, CPU, and the sample-rate change path (the kernel table is rebuilt on sr change).

## 6. Quantitative expected improvements (full-device experiment, `ab_full_device.json`)

Experiment configuration: kernel 0.5 ms, fc 20 kHz, HF comp off. Rows are production → candidate B.

| Metric | Production | Candidate B |
|---|---|---|
| Reported spurs (4 cases) | −10.2 to −56.4 dB | **−97 to −162 dB** |
| Energy outside tone, 48 kHz/17 kHz, FB 5 | −1.4 dB | **−104.5 dB** |
| Energy outside tone, 44.1 kHz, FB 5 | −29.5 dB | −116.6 dB |
| Energy outside tone, modulation INT 2 (48 / 44.1 kHz) | −11 / −26 dB | −95 / −103 dB |
| Default character at nominal (48 / 44.1 kHz; authentic overload remains) | −8.4 / −20.1 dB | −11.2 / −27.4 dB |
| THD (1 kHz) | 0.0041 % | 0.0078 % |
| THD+N | **0.2843 %** | **0.0087 %** (SM typ. 0.03 %) |
| Effect response re 1 kHz, worst point to 17 kHz (48 / 44.1 / 96 kHz) | non-monotonic (HW-3) | −1.69 / −1.84 / −2.80 dB, within the SM +0.5/−3 dB mask |
| Absolute echo time (TIME = T, 48 kHz) | T + 0.0218 ms | T + 0.0027 ms |
| Minimum delay at TIME 0 | 0.02 ms | **0.50 ms** |
| Feedback period @ 50 ms | 50.021–50.042 ms | 50.021–50.042 ms |
| Modulation depth ratio | 0.5041 | 0.5047 |
| CPU, 1 instance, 48 kHz/128 (bench, % one core) | 3.92 % | 6.05 % |
| CPU, 8 instances, 48 kHz/128 | 33.6 % | 58.9 % |
| CPU, 8 instances, 44.1 kHz | 29.1 % | 55.8 % |
| CPU, 1 instance, 96 kHz/128 | 7.65 % | 14.75 % |
| CPU, 8 instances, 96 kHz/128 / 512 | 59.9 / 57.5 % | **123.3 / 94.6 %** |
| Dense mix, 1/3-oct bands 31 Hz–8 kHz | — | ≤ 0.54 dB difference, all 9 programs |
| Dense mix, 10–16 kHz bands | — | up to +2.6 dB (P4, P6, P8) |
| Hats fold-down energy < 4 kHz through programs 1–9 | — | −0 to −5 dB |

Notes on the table:
- The THD rise reflects a slightly different HF path. It is still far below the spec. THD+N falls by a factor of about 33, because the "noise" in production was mostly folded images.
- The modulation depth ratio is unchanged within measurement error.
- CPU rises about 1.7–1.9×. At 96 kHz, 8 instances exceed one core in this single-thread bench. A shorter kernel or a cheaper kernel table interpolation would reduce this.
- The modest fold-down change for hats is because most factory programs' HIGH cut removes HF before it can fold. The large spur reductions matter mainly with bright material and HIGH FLAT/8k.

The hardware-reference suite with the candidate:
- Effect response at 48/96 kHz and total distortion change from INCONSISTENT to **CONSISTENT**.
- Delay rows change to INCONSISTENT only because the suite uses TIME 0 as its latency baseline; absolute delays are more accurate.

## 7. Risks to existing sound and behaviour

1. **TIME 0 / very short times:** a 0.5 ms wet offset gives comb filtering against dry at TIME 0 that the current version does not have. Any flanger-style patches at minimum time would change.
2. **Brighter top octave:** removing the droop and HF comp changes the voicing of programs with open HIGH settings (+2.6 dB at 10–16 kHz). The character is otherwise preserved (≤ 0.54 dB below 8 kHz; quantiser, gain ranging, emphasis and saturation untouched).
3. **More HF regeneration near self-oscillation:** high feedback runs louder and longer at the top (FB 10 peak, FB 6.8 decay). This is a musical-feel change for dub-style runaway use.
4. **CPU:** about 1.7–1.9×; multi-instance 96 kHz sessions are at risk.
5. **Test baselines:**
   - 21 of 51 engine tests fail on the candidate. Most fail by definition: bit-identity A/B tests vs v1.0.1/rc3/rc4, the TIME-0-referenced delay tests, and the 0.5 ms latency test.
   - Five are real behaviour changes (§5 items 2 and 4).
   - None of these tests should be weakened. A production change would need explicit, reviewed re-baselining.
6. **Max/Live untested:** the candidate was only compiled through `gen2c`. gen~ codebox behaviour, the Data sizing at sr change, and real CPU in Live are unverified.
7. **Authenticity:** the original SDD-3000's converter reconstruction is not documented in the service manual available to us. It is unknown whether the 1982 unit produced similar (smaller) image products. The fix targets the emulation artefact (a host-rate/emulated-clock mismatch that hardware cannot have), not a claimed hardware trait. No hardware-equivalence claim is made either way.

## 8. Acceptance criteria (proposed for a future implementation)

| Criterion | Proposed threshold | Basis | Candidate B (experiment) |
|---|---|---|---|
| Non-harmonic spurs, 100 Hz–20 kHz, 44.1/48/96 kHz, −20 dB re nominal | ≤ −80 dB re tone | engineering decision | −97 dB worst ✅ |
| Same with FB 5 and modulation INT 2 | ≤ −70 dB | engineering decision | −95 dB ✅ |
| Effect passband 20 Hz–17 kHz (HIGH FLAT, LOW FLAT) | +0.5 / −3 dB | SM spec | −1.69 / −1.84 / −2.80 dB ✅ |
| Delay accuracy | ±0.05 ms absolute; 1 ms steps | SM (1 ms steps) + engineering | +0.0027 ms ✅ |
| Minimum delay (TIME 0) | ≤ 0.1 ms | engineering decision (preserve current feel) | 0.50 ms ❌ |
| THD (1 kHz, −20 dB re nominal) | ≤ 0.03 % | SM typ. | 0.0078 % ✅ |
| THD+N (same) | ≤ 0.03 % | SM typ. | 0.0087 % ✅ |
| Feedback stability (all loop options, FB 10) | existing bounds unchanged | existing suite | FB 10 peak −13.4 dBFS ❌ |
| Modulation depth/rate | within 1 % of production | engineering decision | 0.12 % ✅ |
| HOLD release timing | existing bound | existing suite | 0.396 ms ❌ |
| NaN/Inf recovery | existing bound | existing suite | 8.1 dB ❌ |
| CPU overhead | ≤ 1.5× production | engineering decision | 1.7–1.9× ❌ |
| Musical character, 31 Hz–8 kHz, factory programs | ≤ 1 dB 1/3-oct difference | engineering decision | ≤ 0.54 dB ✅ |

Candidate B in its experimental form meets the spur, passband, distortion and accuracy targets. It does **not** yet meet the latency, stability-bound, HOLD, NaN and CPU criteria. Those are the work items for any implementation phase.

## 9. Experimental evidence

All under `experiments/hw1/`:

- `results/reproduction.json`: reported cases, sweeps at 44.1/48/96 kHz, nine conditions × 3 rates.
- `results/candidates.json`, `results/taps_tradeoff.json`: isolated model comparison.
- `results/spurs_vs_frequency.png`, `results/spectrum_17k_48k.png`, `results/passband_48k.png`: model plots.
- `results/ab_full_device.json`: full-device A/B covering spurs, conditions, THD/THD+N, timing, modulation, response, CPU and musical bands.
- `results/ab_spurs_full_device.png`, `results/ab_response_full_device.png`, `results/ab_spectrum_17k_48k.png`: full-device plots.
- `results/suites_production_vs_candidate.json`: existing engine suite, run on both engines (no docs written).
- `results/hwref_prod.{json,md}`, `results/hwref_bl.{json,md}`: hardware-reference suite on both engines.
- `audio/*.flac`: A/B renders, production vs candidate B, for:
  - hats through P1/P4/P7;
  - the dense mix through P1/P3/P5.
- CPU: `tests/bench_engine.c` built as `experiments/hw1/build/bench`, numbers in §6. 96 kHz numbers were measured separately and are not in the JSON.

## 10. Files created and inspected

**Created (experiment and report only):**
- `experiments/hw1/README.md`
- `experiments/hw1/reproduce.py`
- `experiments/hw1/convmodel.py`
- `experiments/hw1/evaluate_candidates.py`
- `experiments/hw1/taps_tradeoff.py`
- `experiments/hw1/make_bl.py`: patches a *copy* of the generated genexpr into `experiments/hw1/build/` (not committed).
- `experiments/hw1/compare_bl.py`
- `experiments/hw1/run_suites_bl.py`
- `experiments/hw1/results/*`
- `experiments/hw1/audio/*`
- `docs/validation/HW1_INVESTIGATION.md` (this file)

**Inspected, not modified:**
- `tools/make_gen.py` (coefficients, ADC/tick loop, DAC chain)
- `tools/hfcomp_table.json`
- `tools/gen2c.py`
- `src/gen/echolivity_core.genexpr`
- `tests/engine.py`, `tests/run_tests.py`, `tests/bench_engine.c`
- `tests/hwref/reference_models.py`, `tests/hwref/hw_validation.py`
- `presets/factory_programs.json`
- `docs/TEST_RESULTS.json`: verified byte-identical after all runs.

**Not modified:** `src/`, `tools/`, `tests/`, `presets/`, `dist/`, the device, and the release status.

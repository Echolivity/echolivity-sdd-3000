# HW-1 Remediation: Independent Engineering Audit of Candidate D

| | |
|---|---|
| Audit branch | `audit/hw1-candidate-d`, from `0929250` (main is not modified) |
| Audited artefact | `experiments/hw1/candidate/echolivity_core_d.genexpr` (sha256 `a676f3e7b7e03188186d7118304cb7ef42a286df897ec544a88afd45ba5b122d`) |
| Audited test device | `ECHOLIVITY SDD-3000 HW1-D TEST.amxd` (sha256 `5be387cb3fbb346be7d5ea63fbbc463cf78f4ecc7f5d9863b68f5a9fff6d3649`) |
| Audited engine | Rebuilt from the committed genexpr via `tools/gen2c.py` + `gcc -O2` (`audit/build/engine_cand.so`). Its C source is byte-identical to the qualified build. |
| Baseline | Production C build of `src/gen/echolivity_core.genexpr` (`build/engine.so`), unchanged |
| Environment | Linux cloud VM, 2 vCPU, shared. Python 3.13.18, NumPy 2.5.3, SciPy 1.18.1, Matplotlib 3.11.2, gcc 13.3.0, ffmpeg 6.1.1. **No Max, no Live, no audio interface.** |
| Scripts and raw results | `experiments/hw1/audit/` (scripts) and `experiments/hw1/audit/results/` (raw JSON/CSV and plots) |

## Release decision: **C. REJECTED / FURTHER INVESTIGATION REQUIRED**

Candidate D fixes the original defect. The reported 48 kHz, 17 kHz → 1 kHz spur goes from −10.2 dB to −89.4 dB, and every conversion-image measurement improves by 70–100 dB. It is still not production-ready:

1. **P0 defect: HOLD release starts early.**
   - The crossfade out of the HOLD loop begins 0.042–0.059 ms before one delay time, at every host rate.
   - This breaks the existing timing contract, and the original test fails at 44.1 kHz.
   - The root cause is established and a one-line fix is shown to work (§A), but the fix is not part of the audited candidate.
2. **P0 open: FEEDBACK 10 self-oscillation output offset.**
   - The offset is statistically larger than production: 14 of 30 seeds exceed the original 0.003 limit, against 1 of 30 for production.
   - The previous report wrongly classified this as a measurement defect. The root cause is not established (§B).
3. **P0 not verified: native Max 9 / Live 12.** No native session was run (§E).
4. **The qualification evidence was contradictory.** The previous report contained false PASS statements (Discrepancy Register, §2).
5. **No listening review has taken place** (§G).

---

## 1. Findings by brief section

### A. HOLD release discrepancy (P0): **genuine defect, root cause found**

**Reproduction** (`audit_hold.py`, `results/audit_hold.json`):

- 225 cases per engine: 15 delay times (0–1023 ms) × 44.1 / 48 / 88.2 / 96 / 192 kHz × MONO and TRUE STEREO, per channel.
- The test's own case generator (`tests/run_tests.hold_release_case`) was used unmodified.
- First difference between "released" and "HOLD kept", against the contract t_sw = min(T, 943.9 ms):

| Engine | Worst early start | Cases outside the test's 0.05 ms allowance | Cases earlier than ½ sample |
|---|---|---|---|
| Production | 0.000 ms | 0 / 225 | 0 / 225 |
| **Candidate D** | **0.059 ms** (44.1 kHz). Other rates: 48 kHz 0.042, 88.2 kHz 0.048 ms | **6 / 225**, all at 44.1 kHz, T = 5 and 16 ms (MONO and both TRUE STEREO channels) | **every case with T > 0** |
| D + counterfactual fix | 0.000 ms | 0 / 225 | 0 / 225 |

The figures named in the audit brief (4.943 ms and 15.941 ms, worst 0.059 ms) are reproduced exactly.

**Trace through the code** (candidate genexpr, lines 899 and 1399):

- Latency compensation shortens the normal-tap read offset: `n_tgt = ms·64 − dcmp`, with dcmp = 6 ticks.
- The release state machine still ends the HOLD loop when `relk >= max(na, nb) + 3`. `na` is now the *compensated* offset.
- So the switch to the normal tap, and the start of the 10 ms crossfade, comes dcmp = 6 ticks earlier than in production. Net, the crossfade starts 3 ticks (0.047 ms) before T.
- The minimum-phase output filter begins responding immediately, which adds up to about 0.01 ms.

**Classification:** premature start of the release crossfade. It is neither numerical noise nor a measurement defect.

- The audio faded in early is correctly timed new audio. Its echo time is right; only the transition starts early.
- Audibility at 0.06 ms is implausible, but the timing contract ("identical to HOLD kept until one delay time after release") is violated deterministically at every rate.

**Counterfactual** (`audit/build/echolivity_core_holdfix.genexpr`; a one-line change, *not* applied to the candidate): `relk >= max(na, nb) + dcmp + 3`.

- Worst early deviation 0.000 ms in all 225 cases.
- HOLD, HOLD engage and HOLD re-engage tests still pass (`results/counterfactual_hold_tests.txt`).
- `t_hold_release` still fails, on its separate full-level clause (see B6).

**Previous report:** its claim "all 108 −6 dB cases pass, early deviation 0.000 ms" was **false**. It quoted an earlier calibration build, not the shipped candidate (Discrepancy D1).

### B. Disputed regression classifications (P0)

Every test is reported against its **original** threshold. No threshold was changed and none is proposed as already accepted. Full matrix: `results/regression_matrix.md`.

| ID | Test (original criterion, verbatim from `tests/run_tests.py`) | Candidate D | Production | Audit classification | Evidence |
|---|---|---|---|---|---|
| B1 | Output INV click: `c < max(2.5, 2.0 * c0)` (3rd-difference peak re steady state) | **FAIL** 2.74× | PASS 1.16× | **Proven metric dependence: not a louder click.** D's absolute transient is 2.45e-4, production's 8.96e-4 (D 11 dB smaller). Production's steady-state reference (7.7e-4) is image energy: with the CLEAN converter it is still 7.4e-4, while D's clean reference is 1.8e-5, which gives D 13.3×. The INV ramp code is untouched. For scale, D's transient equals a −78.5 dBFS step; production's equals a −67 dBFS step. | `qualification_d.json` E3; audit run in the log |
| B2 | FB 10 stability: `pk < −13 dBFS and tail_dc < 0.003` | **FAIL** tail 1.2e-2 | PASS 2.7e-3 | **Genuine behaviour difference, root cause NOT established. The previous "measurement defect" label is withdrawn.** Exact combination over 30 seeds: D median 2.8e-3, p90 6.9e-3, max 1.09e-2, **14/30 over the limit**; production median 1.1e-3, max 4.9e-3, **1/30**. The offset decays rather than builds (mean change over the last 4 s: −4.6e-3). It appears only in TRUE STEREO (MONO about 2e-4). It is unchanged with the CLEAN converter, so quantisation is not the cause. Peaks pass (−13.5 dBFS). | `audit_fb10.json`, `fb10_tail_modes.json` |
| B3 | Non-finite input: level after 1.4 s within 0.5 dB | **FAIL** 0.84 dB | PASS 0.32 dB | **Proven test sensitivity.** Output for a ±inf/NaN burst is bit-identical to a finite ±1000 burst (the documented clamp) in both engines, so there is no state corruption. The 0.84 dB is ENV modulation (driven by the +60 dBFS burst) against an FB-6 comb at 440 Hz. At 198/199/200/201/202 ms production reads +0.26 / −6.76 / −0.32 / +6.70 / +0.83 dB; D reads −0.11 / −7.88 / +0.84 / +5.72 / +0.38 dB. Each engine fails 3 of 5 delays. | `qualification_d.json` E4 |
| B4 | Service-manual FB check: `rms(y3) < 1e-4` (8 ms, FB 6.8) | **FAIL** −79.9 dBFS | PASS −81.1 | **Proven test sensitivity.** Both engines stop decaying after about 1.5 s at a 12-bit quantiser limit cycle near −80 dBFS. Production fails the same check at 9 ms (−80.0) and 20 ms (−79.3); D is lower than production at 6, 7, 9 and 20 ms. | Audit run in the log (6–20 ms survey) |
| B5 | Regeneration filters: HIGH 8k at 2·fc in (−9, −6) dB | **FAIL** −9.99 | PASS −8.38 | **Proven measurement dependence.** Tone-only, production is −10.00 dB and D is −10.00 dB: identical. Production's rms reading includes its 16 kHz self-interference image (HW-3). This is the documented HW-2 deviation, already recorded by the hardware-reference suite. | `qualification_d.json` E1 |
| B6 | HOLD release, full nominal level: switchover excess < 3 dB | **FAIL** +4.6/4.7 dB | PASS +1.1 | **Proven: a pre-existing production artefact, unmasked.** Absolute >5 kHz peak at about 129.5 ms (end of the crossfade), channel L: D −61.6 dBFS, production −61.7 dBFS. Production passes only on the level-relative term, because its references carry image HF (never-held reference −76.9 dBFS against D's −93.9). The same burst exists in production. Unchanged by the HOLD fix. | Audit HF profile in the log |
| B7–B9 | Bit-identity A/B (v1.0.1, rc3, rc4) | FAIL | PASS | **Intentional, by definition.** The deafness of INT to the returns is re-verified as bit-exact (max difference 0.0). | `qualification_d.json` E8 |
| B10 | HOLD release early deviation | FAIL (44.1 kHz) | PASS | **Genuine defect** (§A) | `audit_hold.json` |

Proposed test changes. These are for the owner to decide; **none was applied**:

- B1 and B6: compare the absolute transient with the production engine as the non-regression reference.
- B3: replace with the intended property, "invalid input ≡ clamp value, bit-exact".
- B4: sweep the delay time, or set the threshold explicitly above the limit-cycle level.
- B5: measure the tone only, and decide on HW-2.

Each proposal is at least as strict as the current test for the property it is meant to check. None justifies passing B2 or B10.

### C. DSP spectral integrity (P0)

Source: `audit_spectral.py`, `results/audit_spectral.json` and plots `audit_inharmonic.png`, `audit_group_delay.png`, `audit_spectrum_17k_48k.png`.

Coverage:

- host rates 44.1 / 48 / 96 kHz;
- TIME 0 (short path) and TIME 20 (memory path);
- operating points CLEAN/PRE off and defaults (13-bit, PRE on);
- tones 100 Hz–19 kHz at −40 / −20 / −6 dB re nominal;
- two-tone IMD: SMPTE, and CCIF at 19+20 and 13+14 kHz;
- phase and group delay.

**Original defect** (48 kHz, 17 kHz, CLEAN, PRE off, −20 dB re nominal; re tone):

| Path | 1 kHz line | 15 kHz line |
|---|---|---|
| Production | −10.2 dB | −13.4 dB |
| D, TIME 20 | −89.4 dB | −94.3 dB |
| D, TIME 0 | below −155 dB | below −155 dB |

**Fixed.**

**Worst inharmonic line, all tones, linear range** (CLEAN, −40/−20 dB):

| Host rate | Production | D, TIME 20 | D, TIME 0 |
|---|---|---|---|
| 44.1 kHz | −12.0 dB | −86.5 dB | −171.9 dB |
| 48 kHz | −9.0 dB | −88.3 dB | −172.7 dB |
| 96 kHz | −15.6 dB | −112.8 dB | −178.7 dB |

**IMD.**

- CCIF 19+20 kHz at 44.1 kHz, TIME 20, CLEAN: production d2 −60.3 dB with another line at −5.9 dB (images); D d2 −140.7 dB, worst other line −81.3 dB.
- SMPTE at defaults: about −80 dB in both, set by quantisation.

**Defaults (13-bit + PRE).** Inharmonic lines at −40 dB re nominal:

| Host rate | D | Production |
|---|---|---|
| 44.1 kHz | −47.5 dB | −12.0 dB |
| 48 kHz | −42.8 dB | −9.0 dB |
| 96 kHz | −45.9 dB | −15.6 dB |

These are 12-bit quantisation products of a −57 dBFS tone, aliased in the 64 kHz domain (authentic converter behaviour). In the 17 kHz spectrum at defaults they are identical in both engines (about −68 dB re tone).

**THD+N, 1 kHz at −20 dB re nominal, defaults:**

| Host rate | D | Production |
|---|---|---|
| 44.1 kHz | −63.1 dB | −55.6 dB |
| 48 kHz | −66.5 dB | −50.9 dB |
| 96 kHz | −68.7 dB | −66.0 dB |

**Findings that the previous report did not state:**

1. **Low-level quantisation harmonics are not identical to production.**
   - Individual harmonics of 1 kHz at −20 dB re nominal differ by up to ±14 dB (44.1 kHz H3: D −64.3 dB, production −78.6 dB; 96 kHz H3: D −74.7 dB, production −68.0 dB).
   - THD at 44.1 kHz −20 dB: D −63.8 dB, production −72.4 dB.
   - The difference is not systematic in sign. It reflects different values at the quantiser (analog-filtered against linearly interpolated input). Character-relevant at low levels; needs a listening review.
2. **TIME 0 under HF overload is not image-free.**
   - Case: 17–19 kHz at −6 dB re nominal; pre-emphasis drives the converter into clipping.
   - D at TIME 0 shows inharmonic lines at −28 to −30 dB (48 kHz), against −48 dB on D's memory path and −10/−11 dB in production.
   - Cause: the short path box-reconstructs the clipping error, as production does.
   - The previous report's "no images at TIME 0" holds only below overload (Discrepancy D6).
3. **HF overload point differs between paths.**
   - In CCIF 19+20 kHz at 48 kHz, CLEAN, D's TIME-0 path clips (d2 −34.7 dB) while its memory path does not (d2 −251.7 dB).
   - Cause: the analog-prototype input filter lowers the 19–20 kHz peaks before the converter clamp. The memory path therefore has slightly more top-octave headroom than both TIME 0 and production.
4. **Group delay.** At 48 kHz, D rises from 0.001 ms (4 kHz) to 0.058 ms (17 kHz); production from 0.019 to 0.061 ms. At 96 kHz D varies 0.011–0.060 ms against production's 0.027–0.041 ms. D adds dispersion above 10 kHz that accumulates on each regeneration pass (about 0.05 ms per pass).

### D. Timing and delay accuracy (P0)

Source: `audit_timing.py`, `results/audit_timing.json`.

| Item | Production | Candidate D | Status |
|---|---|---|---|
| TIME-0 latency, linear-range impulse (0.005) | 23.5 / 24.4 / 30.6 µs (44.1 / 48 / 96 kHz) | 12.3 / 11.7 / 23.3 µs | PASS (< 50 µs) |
| TIME-0 latency, the test's 0.5 impulse (overloads the converter) | 21.9 / 21.8 / 30.2 µs | 4.0 / 4.1 / 18.8 µs | The previous report's "0.000 ms" was a rounded overload measurement (D3) |
| Echo error 1–1023 ms re TIME, linear range | +23.5 … +26.0 µs | +10.8 … +21.1 µs | PASS |
| Error relative to TIME 0 (test limit 30 µs) | ≤ 2.4 µs | ≤ 9.7 µs (engine suite) | PASS |
| Continuous TIME 0.05 / 0.09 / 0.10 ms (48 kHz) | 0.076 / 0.114 / 0.124 ms | **0.012 / 0.012 / 0.012 ms** (short path) | Known and documented limitation: up to −0.088 ms below 0.1016 ms. Not reachable with authentic 1 ms stepping. |
| Block-size independence (vector 1 / 7 / 64 / 256) | bit-identical | bit-identical | PASS |
| Sample-rate change, state kept (4 transitions) | PASS | PASS (250.010–250.017 ms) | PASS |
| Automation during playback; 90 s fuzz | PASS | PASS | PASS |
| HOLD transitions | PASS | **FAIL** (§A) | FAIL |
| Start-up (fresh instance, first 50 ms) | −2.0 dB (known limitation; production fails) | −2.4 dB | FAIL in both (pre-existing) |

### E. Native Max 9 / Live 12 (P0): **NOT VERIFIED**

No Max 9 or Live 12 session was run for this audit; this environment has neither. None of the following is verified:

- device loading;
- GenExpr compilation in gen~;
- parameter initialisation;
- automation;
- preset loading;
- save/reopen;
- audio-engine restart;
- sample-rate and buffer changes;
- mono/stereo operation;
- multiple instances.

What *is* verified offline:

- static parameter identity: 162/162 parameters, 120/120 program values, banks (`results/test_device_compat.json`);
- the test device rebuilds byte-identically;
- the genexpr compiles through the project's `gen2c` subset translator. That translator is not gen~.

Protocol: `HW1_NATIVE_VALIDATION.md`. Software versions to record: Live 12.x build, Max 9.x build, OS, audio interface and driver.

### F. CPU (P1): measured offline only; **Live NOT VERIFIED**

Source: `audit/bench_pct.c`, `results/cpu_percentiles.csv`.

- Production and D are run *interleaved* per block in one process (alternating order), so VM drift hits both equally.
- Setup is the same as `tests/bench_engine.c`: TRUE STEREO, modulation on, FB 5.
- 20 s sustained per configuration.
- Each cell shows production / D, as % of one core (average) or % of the block period (percentiles).

| Rate | Block | Instances | Average | p50 | p99 | Max | Ratio |
|---|---|---|---|---|---|---|---|
| 44.1 kHz | 64 | 1 | 3.72 / 4.90 | 3.7 / 4.8 | 6.8 / 9.2 | 164.6 / 174.2 | 1.32× |
| 44.1 kHz | 64 | 8 | 29.44 / 39.07 | 29.5 / 39.0 | 45.1 / 62.8 | 295.5 / 180.9 | 1.33× |
| 44.1 kHz | 128 | 1 | 3.55 / 4.67 | 3.5 / 4.6 | 4.3 / 5.6 | 9.0 / 20.4 | 1.32× |
| 44.1 kHz | 128 | 8 | 28.27 / 37.36 | 28.9 / 38.1 | 42.3 / 58.9 | 106.7 / 103.1 | 1.32× |
| 44.1 kHz | 512 | 1 | 3.27 / 4.35 | 3.1 / 4.0 | 5.4 / 7.7 | 9.3 / 16.7 | 1.33× |
| 44.1 kHz | 512 | 8 | 27.36 / 36.10 | 25.8 / 34.2 | 38.2 / 50.6 | 63.0 / 90.8 | 1.32× |
| 48 kHz | 64 | 1 | 3.72 / 4.84 | 3.7 / 4.8 | 5.1 / 6.5 | 32.9 / 31.1 | 1.30× |
| 48 kHz | 64 | 8 | 31.26 / 41.03 | 31.1 / 40.7 | 49.2 / 67.2 | 643.7 / 505.5 | 1.31× |
| 48 kHz | 128 | 1 | 3.47 / 4.54 | 3.3 / 4.3 | 4.7 / 6.1 | 13.9 / 152.8 | 1.31× |
| 48 kHz | 128 | 8 | 31.69 / 41.44 | 31.5 / 41.1 | 49.0 / 67.2 | 413.2 / 146.3 | 1.31× |
| 48 kHz | 512 | 1 | 3.94 / 5.13 | 3.9 / 5.1 | 4.6 / 5.8 | 8.9 / 19.7 | 1.30× |
| 48 kHz | 512 | 8 | 32.99 / 43.17 | 32.3 / 42.1 | 48.1 / 66.5 | 88.9 / 104.2 | 1.31× |
| 96 kHz | 64 | 1 | 7.99 / 9.74 | 7.7 / 9.4 | 12.3 / 16.0 | 246.8 / 943.5 | 1.22× |
| 96 kHz | 64 | 8 | 59.72 / 73.25 | 59.5 / 72.6 | 92.5 / 120.2 | 679.5 / 622.1 | 1.23× |
| 96 kHz | 128 | 1 | 6.44 / 7.78 | 6.3 / 7.6 | 7.7 / 9.3 | 232.1 / 27.8 | 1.21× |
| 96 kHz | 128 | 8 | 61.05 / 74.42 | 61.6 / 74.6 | 92.4 / 117.7 | 1227.0 / 1781.8 | 1.22× |
| 96 kHz | 512 | 1 | 6.93 / 8.50 | 6.6 / 8.0 | 9.4 / 12.3 | 83.3 / 180.5 | 1.23× |
| 96 kHz | 512 | 8 | 60.62 / 73.92 | 61.5 / 74.2 | 92.0 / 117.3 | 132.5 / 168.8 | 1.22× |

**Median.** Interleaved, D's average CPU is 1.21–1.33× production (median 1.31×); its p99 block time is up to 1.43×. This is higher than the previous report's non-interleaved median of 1.25×.

**Worst case.** Maximum block times on this VM are preemption-dominated for both engines (up to 1781 % for D, 1227 % for production) and cannot characterise worst-case behaviour.

**Code inspection** finds no data-dependent cost:

- the tick loop is bounded (`nt < 8`);
- there is no allocation and no table build;
- the sample-rate change computes 6 complex exponentials once.

Eight instances at 96 kHz / 64 exceed one core at p99 in *both* engines in this single-thread worst case; Live spreads tracks across cores. **The target-environment profile remains to be done.**

### G. Factory programs (P1)

Sources: `results/sonic_ab.json` and `results/audit_programs.json`; renders in `experiments/hw1/audio_d/`.

| Measure | Result |
|---|---|
| Gain, per channel, all 9 programs × 4 output modes | Within ±0.01 dB |
| Stereo image | L/R correlation within 0.006; side/mid within 0.05 dB (largest: P8, TRUE STEREO) |
| Frequency response (dense mix, 1/3 octave) | Within 0.30 dB from 31 Hz to 8 kHz. Top octave up to +1.26 dB (16 kHz band, P6) and +0.67 dB (P4), from the intended SM correction at 15–17 kHz and the removal of production's 16 kHz image energy |
| Transients (rimshot repeats, P1/P2/P7/P8) | Peak within 0.57 dB; crest within 0.5 dB; waveform correlation 0.957–0.999 |

Isolated click repeats differ by +1 to +5 dB above 8 kHz. Production's transient top end depends on the click's phase against the tick grid, and D's does not. This is unintended in the sense that it was not designed for; it is a consequence of removing the time-varying behaviour.

Intended changes:

- conversion images removed;
- 17 kHz response brought inside the SM spec;
- latency-compensated timing.

Unintended changes found:

- the low-level quantisation-harmonic pattern (§C finding 1);
- isolated-transient top end;
- top-octave dispersion;
- FB 10 offset (B2).

**Listening review: NOT PERFORMED.** No listening approval is claimed.

### H. Package integrity and reproducibility (P1)

**Rebuilt from a clean clone of `0929250`** (`/tmp/repro`, production built by `tests/engine.py build()`):

- `make_d.py` regenerates the candidate genexpr with an identical sha256 (`a676f3e7…`).
- `build_d.sh` produces byte-identical C.
- `make_test_device.py` produces an identical `.amxd` (`5be387cb…`).
- **`fit_d.py` regenerates `d_calibration.json` bit-exactly**, measured from the production engine and an uncalibrated build.
- No tracked file changed during the rebuild.

**Package gaps:**

- The zip delivered with the remediation report holds `experiments/hw1` and the HW-1 docs only. **It cannot reproduce anything on its own**: it lacks `tools/gen2c.py`, `tools/build_amxd.py`, `tests/` (including `tests/hwref/` models), `src/gen/`, `presets/` and `tests/bench_engine.c`. Reproduction requires the repository at commit `0929250` (or this branch).
- `ffmpeg` is needed only for the FLAC renders.
- No SHA-256 manifest existed before this audit. One is now provided: `results/MANIFEST.sha256`.
- Earlier intermediate builds (d0–d3) are not retained. Their suite results were superseded, but the remediation report quoted some of them (D1, D2).

---

## 2. Discrepancy register

| ID | Statement in `HW1_REMEDIATION_REPORT.md` | Truth (this audit) | Root cause | Severity |
|---|---|---|---|---|
| D1 | "All 108 −6 dB cases pass, early deviation 0.000 ms; excess +0.0 dB" | 6 cases fail; worst 0.059 ms; every rate is early by 0.042–0.059 ms | The report quoted results from an earlier calibration build; the HOLD state machine was not updated for `dcmp` | **P0** |
| D2 | FB 10 "tail mean 9.7e-3 … measurement defect (oscillation-mode statistic)" | The shipped candidate reads 1.2e-2; 14/30 seeds fail against production's 1/30. A genuine difference | Wrong build quoted; under-sampled (18 runs) and over-interpreted | **P0** |
| D3 | "TIME-0 latency 0.000 / 0.000 ms at 44.1/48 kHz" | 0.012 ms in the linear range; 0.004 ms with the test's overloading impulse | Measured with a 0.5 impulse that clips the converter, then rounded | P2 |
| D4 | "There are no genuine regressions remaining" | Two remain (D1, D2) | As D1/D2 | **P0** |
| D5 | "Candidate D passes every C-engine qualification gate except CPU" | Fails HOLD timing and the FB 10 criterion | As D1/D2 | **P0** |
| D6 | "The signal never passes a resampler (no images)" at TIME 0 | True below overload. Under HF overload, TIME 0 shows −28 to −30 dB inharmonic lines (48 kHz) | Clipping error box-reconstructed | P1 |
| D7 | "Converter character preserved"; gain-ranging staircase "within 0.2 dB" | The staircase matches, but individual low-level quantisation harmonics differ by up to ±14 dB | Quantiser input values differ (filtered against interpolated) | P1 |
| D8 | CPU "1.25× median" | 1.31× median interleaved; p99 up to 1.43× | Non-interleaved runs on a noisy VM | P2 |
| D9 | HOLD full-level failure: "measurement defect (reference floor)" | Confirmed, plus a production finding: an identical absolute HF burst (−61.7 dBFS) at the end of the release crossfade exists in production | Pre-existing; masked by images | P2 (production) |
| D10 | A zip of evidence presented as the deliverable | Not self-contained | Packaging | P2 |

## 3. Regression matrix

Full table with verbatim acceptance expressions: `experiments/hw1/audit/results/regression_matrix.md`. Raw data: `results/audit_engine_suite.json`.

| Engine | Engine suite | Hardware-reference suite (CONSISTENT / INCONSISTENT / REPORTED / not comparable) |
|---|---|---|
| Production | 50/51 | 28 / 5 / 8 / 1 |
| Candidate D | 41/51 | 31 / 2 / 8 / 1 |
| D + HOLD counterfactual | 41/51 (`t_hold_release` still fails on clause B6) | — |

## 4. What would change the decision

**To reach B (conditionally approved):**

1. Fix D1 (the one-line change, or equivalent) and re-qualify.
2. Establish and fix the root cause of D2, or demonstrate equivalence to production on the FB 10 offset distribution.
3. The owner decides on the proposed test changes B1 and B3–B6, with the existing thresholds kept for the properties they are meant to check.

**To reach A (approved), additionally:**

4. A native Max 9 / Live 12 run of the full protocol, recording software versions.
5. A CPU profile in Live.
6. A listening review covering the low-level quantisation character, TIME 0 under overload, and the top octave.

**No DSP redesign is indicated.** The architecture achieves its spectral goal, and the defects found are bounded implementation and verification issues.

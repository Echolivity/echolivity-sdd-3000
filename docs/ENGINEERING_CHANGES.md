# ECHOLIVITY SDD-3000 v1.0.2-rc1 — Engineering change report

**Scope:** two DSP defect fixes (HOLD release discontinuity, invalid-input contamination), plus the tests, audio and documentation that prove them. There are no interface, parameter, preset or feature changes.

**Result in one line:** across 47 A/B scenarios and all 19 original demo renders, v1.0.2-rc1 output is **bit-identical** to v1.0.1, except in the two situations that were fixed.

## 1. Files changed

| File | Change |
|---|---|
| `tools/make_gen.py` | HOLD state machine; write fade; normal-tap gate; NaN/Inf guards (generator of the DSP) |
| `src/gen/echolivity_core.genexpr` | regenerated from the above (the code inside gen~) |
| `dist/ECHOLIVITY SDD-3000.amxd`, `src/max/ECHOLIVITY_SDD-3000.maxpat` | rebuilt. **Only the embedded gen~ code differs**; every other patcher object, all 158 Live parameters and the 35 gen~ Params are identical (checked by comparison) |
| `tools/gen2c.py` | test harness accepts `fixnan` (whitelisted GenExpr operator) |
| `tests/engine.py`, `tests/run_tests.py`, `tests/render_examples.py`, `tests/bench_engine.c` | regression tests, v1.0.1 reference build, regression renders, C benchmark |
| `tests/reference/echolivity_core_v1.0.1.genexpr` | the v1.0.1 DSP, kept for A/B comparison |
| `audio_examples/regression/` (8 new WAV files) | v1.0.1 vs v1.0.2 renders |
| documentation | see CHANGELOG |

**Unchanged:** `presets/factory_programs.json`, `tools/build_amxd.py`, `tools/hfcomp_table.json`, the interface, all parameter names/IDs/ranges, and all 19 existing audio examples (bit-identical).

## 2. Defect 1 — HOLD release discontinuity

### Root cause (v1.0.1)
While HOLD is engaged, the memory write pointer `w` keeps advancing without writing. On release, writing restarts at that arbitrary `w` and the normal tap reads `w − N` (frozen memory). Two discontinuities follow:
1. **One delay time after release**, the tap reaches the address where writing resumed: an abrupt jump from old to new audio.
2. If the frozen region contains the HOLD loop's **raw seam** (newest sample next to oldest), the tap crosses it.

The same frozen memory also meant that **re-engaging HOLD within ~1 s** captured the old raw seam into the new loop, giving a click once per loop cycle.

Measured: 2.8–6.9× the steady-state sample step after release; +27 to +35 dB click excess (>5 kHz) on tones; +30 dB on a sustained chord.

### Fix (v1.0.2), `tools/make_gen.py`, HOLD section
A state machine `hst`: 0 = normal, 1 = held, 2 = releasing (loop audible), 3 = releasing (loop faded early).

| Step | Behaviour |
|---|---|
| Engage (from normal) | **Unchanged from v1.0.1**: loop = last 1008 ms, continues from the current tap, 5 ms linear crossfade, writes stop at once. |
| Release | The HOLD loop **keeps playing**. Writing restarts **one word behind the HOLD reader**, so it never overwrites words the loop still has to play. New writes fade in over 4 ms (smoothstep blend with the memory content). The normal tap is muted. |
| Normal tap reads only new audio (one delay time after release) | 10 ms smoothstep crossfade from the loop to the normal tap. From here on, operation is exactly normal: with FEEDBACK 0 the output equals a never-held run at −240 dB. |
| Delays > ~944 ms | The writer (one delay time of new audio) plus the reader (which skips the 1024-word seam gap) need more than the 64K-word memory. The loop is therefore faded out (10 ms smoothstep) before the reader could reach new audio, and the normal tap fades in when it reads only new audio. **Gap of up to ~79 ms** between loop and first new echo (T = 1023 ms). |
| HOLD pressed again while the loop is still audible (release window or fade) | Loop keeps playing with no jump; the writes fade out over 4 ms. A reversal in the middle of the 10 ms fade keeps the smoothstep weighting, so the mix weight stays continuous. |
| Release less than 5 ms after engage | Deferred until the 5 ms engage ramp completes. |

Why this preserves the original behaviour: while HOLD is engaged nothing changes. After release, timing is exact: the first new echo arrives exactly T after release (tested at −180 dB), with no added latency. The loop never jumps, and the normal tap never reads stale memory, so the old raw seam can no longer be heard or captured.

## 3. Defect 2 — invalid input contaminating DSP state

### Root cause (v1.0.1)
There was no sanitising. One NaN or ±inf input sample entered the recursive filters, the feedback path and the 64K-word memory, and stayed there permanently. Output was NaN until the device was reloaded.

### Fix (v1.0.2)
- Input: `in = clamp(fixnan(in), −1000, 1000)`. NaN becomes 0; ±inf becomes ±1000 (+60 dBFS), which the preamp, converter and safety curve then handle like any overload.
- Every History is stored through `fixnan()`. Every converter word is `fixnan()`-ed before it is written to memory. The delay-target computation and all five outputs are guarded.
- `fixnan(x)` returns `x` unchanged for every non-NaN value, and the clamp is inactive below +60 dBFS. **Valid audio is processed bit-identically** (proven by the A/B tests).
- Recovery is immediate: the invalid sample contributes 0, and normal audio continues on the next sample. Invalid input played over an engaged HOLD leaves the loop bit-identical.

## 4. Intentional sonic differences (complete list)

| # | Situation | v1.0.1 | v1.0.2-rc1 |
|---|---|---|---|
| 1 | Releasing HOLD | 5 ms crossfade into frozen memory; a click one delay time later (and possibly at the old seam) | loop continues for one delay time, then a 10 ms smoothstep crossfade into the new echoes; no click |
| 2 | Releasing HOLD with TIME > ~944 ms | as 1 | loop fades out at ~944 ms; new echoes fade in at T (gap ≤ ~79 ms) |
| 3 | With FEEDBACK > 0, during the release window | frozen memory was regenerated | the audible loop is regenerated into the new echoes (it decays naturally through FEEDBACK) |
| 4 | HOLD pressed again while the released loop is still audible | new loop captured from frozen memory (click per cycle) | loop continues; new audio written during the window is blended in and out (4 ms) |
| 5 | HOLD released < 5 ms after engaging | immediate | after the 5 ms engage ramp |
| 6 | NaN / ±inf input sample | permanent NaN output | sample treated as 0 / ±1000, processing continues |
| 7 | Finite input beyond ±1000 (+60 dBFS) | processed | clamped to ±1000 (already deep in saturation either way) |

Nothing else differs. There is no difference in delay timing, feedback, filters, modulation, converter, preamp, outputs, BYPASS, HOLD while engaged, sample-rate handling, CPU (within measurement noise) or latency.

## 5. Evidence

- `docs/TEST_REPORT.md`: 41 engine tests, all PASS, including the 108-case HOLD-release matrix (12 delay times × 44.1/48/96 kHz × MONO/TRUE STEREO), special cases, the re-engage test, NaN/Inf recovery, and the 47-scenario A/B bit-identity test.
- The click metric is validated: applied to the v1.0.1 engine it flags the defect at +27.0 / +34.6 dB.
- `audio_examples/regression/`: four v1.0.1/v1.0.2 pairs; measurements in the test report.

## 6. Risk assessment

| Risk | Mitigation / status |
|---|---|
| gen~ compiles `fixnan` differently, or the code fails to compile | `fixnan` is a standard gen~ operator; the code passes the conservative GenExpr subset checks. **gen~ compilation NOT VERIFIED** (no Max here) |
| CPU increase | C build: no measurable change (−12 % … +15 %, noise on a shared VM) |
| Behaviour while HOLD is engaged changes | A/B: HOLD-engage scenario bit-identical; engage code path unchanged |
| Memory overrun from the new pointer logic | bounds counter on every access = 0 in all tests (incl. 30 s stress at 22.05–192 kHz) |

---

## Addendum: hardware-reference validation methodology (after rc5)

No implementation change. Validation now has a third, independent axis besides the engine regression suite and static checks: the software against the **1982 documentation**. Its parts are:

- reference models: `tests/hwref/reference_models.py`
- suite: `tests/hwref/hw_validation.py`
- evidence and method: `docs/validation/HARDWARE_REFERENCE.md`

The suite found three implementation characteristics that the regression suite couldn't see, because it compares against the implementation's own history and measures only fundamentals:
- in-band alias images from the 64 kHz → host-rate conversion (HW-1);
- warping of the bilinear HIGH cut at the host rate (HW-2);
- a marginal 17 kHz response at 48 / 96 kHz (HW-3).

Fixing any of them would change the sound and the bit-identical baselines, so each needs a separate, approved task with listening.


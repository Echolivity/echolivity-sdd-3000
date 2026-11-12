# DSP regression report — v1.0.2-rc4

**rc4 update:** the DSP gained the external regeneration loop (FB ROUTE / RETURN, in 3/4, out 6/7). With FB ROUTE = INT (default), outputs 1–5 are bit-identical to rc1/rc2/rc3, including with noise, NaN or inf on the return inputs (test 45, against `tests/reference/echolivity_core_v1.0.2-rc3.genexpr`). Full suite: 46/47 PASS, 1 known (D-3); tests 45–47 cover the new path. The sections below are from the rc2 validation round.


Executed in this validation round on the C translation of the exact gen~ code embedded in the device (`tools/gen2c.py`); not in Live. Full suite: **43/44 PASS, 1 known-limitation FAIL (D-3), 0 unexpected FAIL**.

## Comparison against baselines

- **rc1 baseline:** the 41 rc1 tests were re-run. PASS/FAIL is identical and every measurement is identical to the shipped rc1 results (CPU timings excluded). Tests 42–44 are new.
- **v1.0.1 baseline:** test 39 runs the v1.0.1 DSP (`tests/reference/`) and rc1 on identical input. 47/47 scenarios are bit-identical; the only differences are the two documented fixes (HOLD release, invalid input).
- **Audio:** all 19 v1.0.1 demo WAVs and all 8 rc1 regression WAVs re-render bit-identically (reproducibility check).

## Requested items → tests

| Item | Tests (number: status) |
|---|---|
| HOLD release transitions | 37. HOLD release transition: PASS; 29. HOLD engage transition: PASS |
| HOLD re-engagement during release | 37. HOLD release transition: PASS; 38. HOLD re-engaged shortly after a completed release: PASS |
| NaN and Infinity protection | 35. non-finite audio input (NaN / +inf / -inf): PASS; 36. NaN parameter values (C model): PASS; 34. huge finite input sample (1e30): PASS |
| Feedback stability | 26. feedback 10 stability across all loop options: PASS; 20. no uncontrolled runaway / DC accumulation: PASS; 21. service-manual feedback check: PASS; 9. feedback decay per repeat: PASS |
| Delay-time changes | 19. parameter changes are click-free: PASS; 2. delay time accuracy @ 48000 Hz: PASS; 6. authentic 1 ms stepping: PASS; 7. tempo sync divisions: PASS |
| Buffer boundaries | 32. memory / buffer boundary safety: PASS; 24. random automation fuzz (90 s, 1800 changes): PASS; 44. block-size independence (C harness): PASS |
| Dry/wet behaviour | 42. dry/wet balance law: PASS; 17. BYPASS (direct only, clears loop): PASS; 30. BYPASS transitions and residual wet signal: PASS |
| Stereo integrity | 18. stereo / phase output modes: PASS; 28. TRUE STEREO channel isolation: PASS |
| Parameter limits | 33. out-of-range parameter values: PASS; 36. NaN parameter values (C model): PASS |
| Comparison vs v1.0.1 | 39. A/B regression v1.0.2 vs v1.0.1 (identical input and settings): PASS |

## Full results

| # | Test | Status | In rc1 | Measured |
|---|---|---|---|---|
| 1 | delay time accuracy @ 44100 Hz | PASS | yes | worst error 1.6 us over 1..1023 ms (system latency 0.022 ms) |
| 2 | delay time accuracy @ 48000 Hz | PASS | yes | worst error 0.0 us over 1..1023 ms (system latency 0.022 ms) |
| 3 | delay time accuracy @ 88200 Hz | PASS | yes | worst error 6.6 us over 1..1023 ms (system latency 0.032 ms) |
| 4 | delay time accuracy @ 96000 Hz | PASS | yes | worst error 0.0 us over 1..1023 ms (system latency 0.030 ms) |
| 5 | delay time accuracy @ 192000 Hz | PASS | yes | worst error 0.0 us over 1..1023 ms (system latency 0.031 ms) |
| 6 | authentic 1 ms stepping | PASS | yes | 100.4 ms requested -> authentic 100.000 ms, continuous 100.398 ms |
| 7 | tempo sync divisions | PASS | yes | 120 BPM 1/8=250.00, 3/8=750.00 ms; 100 BPM 1/4=600.00 ms; 60 BPM 1/1 clamped to 1023.00 ms |
| 8 | effect frequency response | PASS | yes | 20 Hz -0.26 dB, 50 Hz -0.04 dB, 100 Hz -0.01 dB, 1000 Hz -0.09 dB, 5000 Hz -0.67 dB, 10000 Hz -1.06 dB, 15000 Hz -2.21 dB, 17000 Hz -2.86 dB, 20000 Hz -4.97 dB |
| 9 | feedback decay per repeat | PASS | yes | FB 2.0: -10.97 dB/repeat (expected -10.88); FB 3.5: -6.11 dB/repeat (expected -6.02); FB 5.0: -3.01 dB/repeat (expected -2.92); FB 6.5: -0.74 dB/repeat (expected -0.64) |
| 10 | regeneration filter responses | PASS | yes | HIGH 8000 Hz: -3.01 dB at fc, -8.38 dB at 2fc; HIGH 4000 Hz: -2.97 dB at fc, -7.44 dB at 2fc; HIGH 2000 Hz: -2.97 dB at fc, -7.04 dB at 2fc; LOW 125 Hz: -2.97 dB at fc, slope 2.92 dB/oct below; LOW 250 Hz: -2.94 dB at fc, slope 2.84 dB/oct below; LOW 500 Hz: -… |
| 11 | filters act inside the feedback loop | PASS | yes | 4000 Hz burst: filtered/flat per repeat -7.1 -14.2 -21.4 -28.5 -35.7 dB; 125 Hz burst: filtered/flat per repeat -8.5 -17.0 -25.5 -33.9 -42.4 dB |
| 12 | modulation rate range | PASS | yes | FREQ 0: 0.100 Hz (target 0.100); FREQ 3: 0.450 Hz (target 0.450); FREQ 5: 1.225 Hz (target 1.225); FREQ 10: 15.000 Hz (target 15.000) |
| 13 | modulation depth (delay shortening) | PASS | yes | INT 10: 200.0 ms of 400 ms (50.0%, expected 50.0%); INT 5: 266.7 ms of 400 ms (66.7%, expected 66.7%); INT 2: 333.3 ms of 400 ms (83.3%, expected 83.3%) |
| 14 | modulation waveforms | PASS | yes | TRI: curvature peak/trough = 78.8x (sharp top, rounded bottom); SQUARE: 98.9% of time at 0/1; RND @5.5 Hz: std 0.239, max step/sample 1.37e-04, energy >50 Hz -39 dB re signal |
| 15 | envelope follower | PASS | yes | nominal tone -> 0.99 of full swing, -20 dB tone -> 0.10; release tau 1.44 s |
| 16 | HOLD (infinite repeat) | PASS | yes | loop period 1008.0 ms, level spread over 4 loops 0.00 dB, new input leakage -240 dB, seam jump 1.27x of 99.9th pct step |
| 17 | BYPASS (direct only, clears loop) | PASS | yes | wet during bypass (after 250 ms) -195 dBFS, after release -240 dBFS, direct at BALANCE 10 -0.00 dB |
| 18 | stereo / phase output modes | PASS | yes | output INV: sum+difference = 2x direct (residual -82 dB); STEREO A: L=DIRECT (-240 dB), R=+MIX (-240 dB); STEREO B: L=+MIX, R=-MIX, mono sum cancels wet (-82 dB); TRUE STEREO: L->R crosstalk -240 dB; WIDTH 0 -> mono |
| 19 | parameter changes are click-free | PASS | yes | [metric self-check: -60 dB step scores 222x]; delay time 380->120 ms (crossfade): 1.13x; delay time 380->120 ms (glide): 2.11x; feedback 2->8: 0.98x; regen INV: 0.22x; LOW FLAT->500: 0.91x; HIGH FLAT->2k: 0.94x; HIGH 8k->2k: 0.82x; balance 2->9: 0.97x; output … |
| 20 | no uncontrolled runaway / DC accumulation | PASS | yes | FB 10 sat=hard: peak -14.0 dBFS, DC 1.2e-03, finite=True; FB 10 sat=soft: peak -14.3 dBFS, DC 9.9e-05, finite=True |
| 21 | service-manual feedback check | PASS | yes | FB 10 / 50 ms / 500 Hz+2 kHz: sustained oscillation -18 dBFS after 5 s; no input -> output exactly 0 (0.0); 8 ms flat FB 6.8 decays (-81 dBFS) |
| 22 | preamp / input stage | PASS | yes | ATT -30: 1 dB compression at -13.5 dBm (spec clip -13 dBm); ATT -10: 1 dB compression at +6.5 dBm (spec clip +7 dBm); ATT +4: 1 dB compression at +20.5 dBm (spec clip +21 dBm); delay BYPASS + drive: 3rd harmonic 10 dB (preamp active); character OFF at 0 dBFS: … |
| 23 | 13-bit gain-ranged converter | PASS | yes | 13-bit vs clean at nominal: noise 77.1 dB below signal; -26 dB signal: noise 62.3 dB below signal (gain-ranged 13-bit) |
| 24 | random automation fuzz (90 s, 1800 changes) | PASS | yes | finite=True, peak 12.0 dBFS (out gain up to +12 dB), memory bounds errors 0 |
| 25 | CPU (C build of the gen~ code, 48 kHz stereo) | PASS | yes | 22x real-time on this machine's single core (~4.48% of one core; includes Python block overhead) |
| 26 | feedback 10 stability across all loop options | PASS | yes | flat: peak -13.8 dBFS, tail DC 8.1e-05; {'fb_inv': 1}: peak -13.8 dBFS, tail DC 1.8e-04; {'lowcut': 3, 'highcut': 3}: peak -15.6 dBFS, tail DC 9.2e-05; {'lowcut': 0, 'highcut': 0, 'lc_slope': 1}: peak -13.7 dBFS, tail DC 5.2e-04; {'loop_sat': 1}: peak -14.1 dB… |
| 27 | parameter changes during active playback | PASS | yes | per-vector random automation 20 s: finite=True, peak -5.2 dBFS, bounds errors 0; ramp feedback 0->9: 0.15x; ramp balance 0->10: 1.01x; ramp intensity 0->10: 1.10x; ramp in_level 2->8: 0.55x; ramp drive 0->24: 1.09x; ramp width 0->2: 0.99x; ramp out_gain -24->1… |
| 28 | TRUE STEREO channel isolation | PASS | yes | WAVE TRI: R->L -240 dB (rounding only), L->R with silent R: -240 dB (rounding only); WAVE SQR: R->L -240 dB (rounding only), L->R with silent R: -240 dB (rounding only); WAVE RND: R->L -240 dB (rounding only), L->R with silent R: -240 dB (rounding only); WAVE … |
| 29 | HOLD engage transition | PASS | yes | T=5 ms: 1.00x; T=120 ms: 1.00x; T=380 ms: 0.73x; T=1008 ms: 1.09x; T=1023 ms: 0.83x |
| 30 | BYPASS transitions and residual wet signal | PASS | yes | wet residual after BYPASS on: 50 ms -43 dBFS, 100 ms -72 dBFS, 150 ms -101 dBFS, 300 ms -192 dBFS; BYPASS on during playback: 0.76x; BYPASS off during playback: 0.01x; after >1.023 s bypassed, release outputs no stale echo (peak -240 dBFS) |
| 31 | host sample-rate change (state kept) | PASS | yes | 48000->96000 Hz without reset: delay 250.012 ms, finite=True; 96000->44100 Hz without reset: delay 250.017 ms, finite=True; 44100->192000 Hz without reset: delay 250.010 ms, finite=True; 192000->48000 Hz without reset: delay 250.017 ms, finite=True |
| 32 | memory / buffer boundary safety | PASS | yes | 44100 Hz {'time_ms': 1023, 'waveform': 1, 'intensity': 10, 'frequency': 10}: 30 s, memory wraps ~58x, bounds errors 0, finite=True; 192000 Hz {'time_ms': 0, 'waveform': 0, 'intensity': 10, 'frequency': 10}: 30 s, memory wraps ~58x, bounds errors 0, finite=True… |
| 33 | out-of-range parameter values | PASS | yes | values far outside the range are clamped to min/max (harness mirrors gen~ Param min/max); output finite |
| 34 | huge finite input sample (1e30) | PASS | yes | output stays finite and below the ceiling (peak -1.8 dBFS), recovers |
| 35 | non-finite audio input (NaN / +inf / -inf) | PASS | yes | single NaN: all outputs finite, level after 1.4 s within 0.00 dB of clean; single +inf: all outputs finite, level after 1.4 s within 0.00 dB of clean; single -inf: all outputs finite, level after 1.4 s within 0.00 dB of clean; 1000 NaN samples: all outputs fin… |
| 36 | NaN parameter values (C model) | PASS | yes | 23 parameters set to NaN for 0.3 s then restored: output finite throughout and audio resumes; failures: none. Whether gen~ Param clamping lets NaN through is NOT VERIFIED. |
| 37 | HOLD release transition | PASS | yes | 108 cases (12 delay times x 44.1/48/96 kHz x MONO/TRUE STEREO, per channel, -6 dB input): output identical (-180 dB) to 'HOLD kept' until one delay time after release, or until ~944 ms for longer delays (worst early deviation 0.000 ms); worst click excess (>5 … |
| 38 | HOLD re-engaged shortly after a completed release | PASS | yes | T=5 gap 50 ms: step 1.03x / spike 11.9 dB (first-ever HOLD 1.01x / 12.9 dB; v1.0.1 4.50x / 37.7 dB); T=16 gap 100 ms: step 1.13x / spike 12.9 dB (first-ever HOLD 1.19x / 13.3 dB; v1.0.1 2.84x / 37.0 dB); T=50 gap 50 ms: step 1.00x / spike 11.5 dB (first-ever H… |
| 39 | A/B regression v1.0.2 vs v1.0.1 (identical input and settings) | PASS | yes | 47 scenarios (9 programs x 4 output modes, 5 host rates, PRE on/off, clean/13-bit, extremes, HOLD engage, BYPASS, random automation): 47 bit-identical (all 5 outputs incl. meters/display) / intentional difference 1 (HOLD release): T=120: v1.0.1 worst step 10.1… |
| 40 | processing latency | PASS | yes | 44100 Hz: direct path 0 samples; effect path at TIME 0 = 0.022 ms (1.0 samples, filter group delay); 48000 Hz: direct path 0 samples; effect path at TIME 0 = 0.022 ms (1.0 samples, filter group delay); 96000 Hz: direct path 0 samples; effect path at TIME 0 = 0… |
| 41 | CPU of the C build per host rate (stereo, modulation on) | PASS | yes | 44100 Hz: 20x real-time (4.98% of one core); 48000 Hz: 19x real-time (5.38% of one core); 88200 Hz: 12x real-time (8.19% of one core); 96000 Hz: 11x real-time (8.89% of one core); 192000 Hz: 5x real-time (18.98% of one core). Standalone benchmark of the transl… |
| 42 | dry/wet balance law | PASS | new | BALANCE 0: dry 1.000 (exp 1.00), wet 0.000 (exp 0.00); BALANCE 2.5: dry 1.000 (exp 1.00), wet 0.495 (exp 0.50); BALANCE 5: dry 1.000 (exp 1.00), wet 0.990 (exp 1.00); BALANCE 7.5: dry 0.500 (exp 0.50), wet 0.990 (exp 1.00); BALANCE 10: dry 0.000 (exp 0.00), we… |
| 43 | start-up: no undelayed wet signal after instantiation | FAIL (known, D-3) | new | fresh engine, effect only: output during the first 50 ms is -10.9 dB re input (identical in v1.0.1); exactly silent after 50 ms of settling |
| 44 | block-size independence (C harness) | PASS | new | block sizes 32: identical, 64: identical, 128: identical, 256: identical, 512: identical, 1024: identical, 2048: identical (parameter changes at block-aligned times, incl. HOLD) |

Complete measurement text: `docs/TEST_RESULTS.json` and `docs/TEST_REPORT.md`.

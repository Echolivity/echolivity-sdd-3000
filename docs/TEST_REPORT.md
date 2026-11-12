# ECHOLIVITY SDD-3000 v1.0.2-rc5 — Test and validation report

Status vocabulary: **PASS** = verified by an automated test or check. **FAIL** = the check fails (all current FAILs are known limitations of the unchanged v1.0 DSP, documented below). **NOT VERIFIED** = needs Max/Ableton Live, which was not available in the build environment. Static inspection is reported as *PASS (static)* and is never presented as runtime validation. Release-candidate status: the DSP acceptance criteria are met; Ableton Live validation is OUTSTANDING (`docs/LIVE_VALIDATION_CHECKLIST.md`).

## Summary

| Area | Result |
|---|---|
| Engine tests (C build of the exact gen~ code) | 50 PASS, 1 FAIL (known limitation), 0 unexpected FAIL — 51 total |
| Static device checks (`tools/inspect_amxd.py`) | 20/20 PASS (static) |
| Reproducibility (`tools/verify_release.py`) | 8/8 PASS |
| Runtime behaviour inside Ableton Live / Max | 15 items BLOCKED (no Live available) |
| Release decision | CONDITIONAL PASS, not production-ready (`docs/validation/RELEASE_DECISION.md`) |

## 1. Engine tests

`tools/gen2c.py` compiles the GenExpr embedded in the device to C, after enforcing a conservative GenExpr subset (whitelisted operators, depth-0 locals, no History read-after-write, no History writes in loops, no ternaries or `%`). Parameters are applied at 64-sample vector boundaries, as in gen~. Tests 1–25 are the v1.0 suite (measurements unchanged); 26–37 were added in v1.0.1; 38–41 in v1.0.2 (HOLD release matrix, re-engage, A/B regression against the v1.0.1 DSP, latency, per-rate CPU). Tests 30, 36 and 37 were known-limitation FAILs in v1.0.1 and are acceptance tests now; 42–44 were added in the final validation round (43 documents the pre-existing minor defect D-3). Source: `tests/run_tests.py`.

| # | Test | Status | Measured | Reference |
|---|---|---|---|---|
| 1 | delay time accuracy @ 44100 Hz | PASS | worst error 1.6 us over 1..1023 ms (system latency 0.022 ms) | 0-1023 ms, 1 ms step |
| 2 | delay time accuracy @ 48000 Hz | PASS | worst error 0.0 us over 1..1023 ms (system latency 0.022 ms) | 0-1023 ms, 1 ms step |
| 3 | delay time accuracy @ 88200 Hz | PASS | worst error 6.6 us over 1..1023 ms (system latency 0.032 ms) | 0-1023 ms, 1 ms step |
| 4 | delay time accuracy @ 96000 Hz | PASS | worst error 0.0 us over 1..1023 ms (system latency 0.030 ms) | 0-1023 ms, 1 ms step |
| 5 | delay time accuracy @ 192000 Hz | PASS | worst error 0.0 us over 1..1023 ms (system latency 0.031 ms) | 0-1023 ms, 1 ms step |
| 6 | authentic 1 ms stepping | PASS | 100.4 ms requested -> authentic 100.000 ms, continuous 100.398 ms | 1 ms step (authentic) / continuous (modern) |
| 7 | tempo sync divisions | PASS | 120 BPM 1/8=250.00, 3/8=750.00 ms; 100 BPM 1/4=600.00 ms; 60 BPM 1/1 clamped to 1023.00 ms | modern |
| 8 | effect frequency response | PASS | 20 Hz -0.26 dB, 50 Hz -0.04 dB, 100 Hz -0.01 dB, 1000 Hz -0.09 dB, 5000 Hz -0.67 dB, 10000 Hz -1.06 dB, 15000 Hz -2.21 dB, 17000 Hz -2.86 dB, 20000 Hz -4.97 dB | Effect 20 Hz-17 kHz +0.5/-3 dB |
| 9 | feedback decay per repeat | PASS | FB 2.0: -10.97 dB/repeat (expected -10.88); FB 3.5: -6.11 dB/repeat (expected -6.02); FB 5.0: -3.01 dB/repeat (expected -2.92); FB 6.5: -0.74 dB/repeat (expected -0.64) | loop gain = FEEDBACK/7 (oscillation above ~7) |
| 10 | regeneration filter responses | PASS | HIGH 8000 Hz: -3.01 dB at fc, -8.38 dB at 2fc; HIGH 4000 Hz: -2.97 dB at fc, -7.44 dB at 2fc; HIGH 2000 Hz: -2.97 dB at fc, -7.04 dB at 2fc; LOW 125 Hz: -2.97 dB at fc, slope 2.92 dB/oct below; LOW 250 Hz: -2.94 dB at fc, slope 2.84 dB/oct below; LOW 500 Hz: -2.94 dB at fc, slope 2.88 dB/oct below; LOW 500 Hz alt -6 dB/oct: -2.97 dB at fc, slope 5.30 dB/oct | LOW 125/250/500 Hz -3 dB/oct, HIGH 8k/4k/2k -6 dB/oct (service manual) |
| 11 | filters act inside the feedback loop | PASS | 4000 Hz burst: filtered/flat per repeat -7.1 -14.2 -21.4 -28.5 -35.7 dB; 125 Hz burst: filtered/flat per repeat -8.5 -17.0 -25.5 -33.9 -42.4 dB | each repeat is filtered again (progressive) |
| 12 | modulation rate range | PASS | FREQ 0: 0.100 Hz (target 0.100); FREQ 3: 0.450 Hz (target 0.450); FREQ 5: 1.225 Hz (target 1.225); FREQ 10: 15.000 Hz (target 15.000) | VCO 0.1-15 Hz (FREQ 0 = 10 s period) |
| 13 | modulation depth (delay shortening) | PASS | INT 10: 200.0 ms of 400 ms (50.0%, expected 50.0%); INT 5: 266.7 ms of 400 ms (66.7%, expected 66.7%); INT 2: 333.3 ms of 400 ms (83.3%, expected 83.3%) | INTENSITY 0-2:1, delay only shortens (100%->50%) |
| 14 | modulation waveforms | PASS | TRI: curvature peak/trough = 78.8x (sharp top, rounded bottom); SQUARE: 98.9% of time at 0/1; RND @5.5 Hz: std 0.239, max step/sample 1.37e-04, energy >50 Hz -39 dB re signal | triangle / square / smoothed random |
| 15 | envelope follower | PASS | nominal tone -> 0.99 of full swing, -20 dB tone -> 0.10; release tau 1.44 s | delay shortens as input rises; ~2 s decay (SM Fig.4) |
| 16 | HOLD (infinite repeat) | PASS | loop period 1008.0 ms, level spread over 4 loops 0.00 dB, new input leakage -240 dB, seam jump 1.27x of 99.9th pct step | infinite repeat of last ~1 s; input locked out; no degradation |
| 17 | BYPASS (direct only, clears loop) | PASS | wet during bypass (after 250 ms) -195 dBFS, after release -240 dBFS, direct at BALANCE 10 -0.00 dB | all outputs direct; bypass clears an overdub (owner's manual) |
| 18 | stereo / phase output modes | PASS | output INV: sum+difference = 2x direct (residual -82 dB); STEREO A: L=DIRECT (-240 dB), R=+MIX (-240 dB); STEREO B: L=+MIX, R=-MIX, mono sum cancels wet (-82 dB); TRUE STEREO: L->R crosstalk -240 dB; WIDTH 0 -> mono | +MIX/MONO, -MIX, DIRECT, output INV (owner's manual) |
| 19 | parameter changes are click-free | PASS | [metric self-check: -60 dB step scores 222x]; delay time 380->120 ms (crossfade): 1.13x; delay time 380->120 ms (glide): 2.11x; feedback 2->8: 0.98x; regen INV: 0.22x; LOW FLAT->500: 0.91x; HIGH FLAT->2k: 0.94x; HIGH 8k->2k: 0.82x; balance 2->9: 0.97x; output INV: 1.16x; input ATT +4 -> -10: 0.06x; output mode MONO->STEREO B: 0.97x; HOLD on: 0.70x; BYPASS on: 0.98x; waveform TRI->SQUARE (INT 3): 1.02x; converter 13-bit->clean: 0.97x; tempo sync on: 0.29x; preamp character off: 0.98x; loop saturation on: 1.00x | 3rd-difference transient within 2.5x of steady state |
| 20 | no uncontrolled runaway / DC accumulation | PASS | FB 10 sat=hard: peak -14.0 dBFS, DC 1.2e-03, finite=True; FB 10 sat=soft: peak -14.3 dBFS, DC 9.9e-05, finite=True | self-oscillation is bounded by the converter (or soft limiter) |
| 21 | service-manual feedback check | PASS | FB 10 / 50 ms / 500 Hz+2 kHz: sustained oscillation -18 dBFS after 5 s; no input -> output exactly 0 (0.0); 8 ms flat FB 6.8 decays (-81 dBFS) | SM 7.7: oscillates with pulse at FB 10; no oscillation with LEVEL 0 |
| 22 | preamp / input stage | PASS | ATT -30: 1 dB compression at -13.5 dBm (spec clip -13 dBm); ATT -10: 1 dB compression at +6.5 dBm (spec clip +7 dBm); ATT +4: 1 dB compression at +20.5 dBm (spec clip +21 dBm); delay BYPASS + drive: 3rd harmonic 10 dB (preamp active); character OFF at 0 dBFS: highest harmonic -125 dB | SM spec: max input -13/+7/+21 dBm @ LEVEL 5 |
| 23 | 13-bit gain-ranged converter | PASS | 13-bit vs clean at nominal: noise 77.1 dB below signal; -26 dB signal: noise 62.3 dB below signal (gain-ranged 13-bit) | 12-bit DAC + 1 range bit; effect S/N 88 dB(A) spec incl. emphasis |
| 24 | random automation fuzz (90 s, 1800 changes) | PASS | finite=True, peak 12.0 dBFS (out gain up to +12 dB), memory bounds errors 0 | stability, no buffer overruns |
| 25 | CPU (C build of the gen~ code, 48 kHz stereo) | PASS | 16x real-time on this machine's single core (~6.13% of one core; includes Python block overhead) | efficient; gen~ in Live must be measured separately |
| 26 | feedback 10 stability across all loop options | PASS | flat: peak -13.8 dBFS, tail DC 8.1e-05; {'fb_inv': 1}: peak -13.8 dBFS, tail DC 1.8e-04; {'lowcut': 3, 'highcut': 3}: peak -15.6 dBFS, tail DC 9.2e-05; {'lowcut': 0, 'highcut': 0, 'lc_slope': 1}: peak -13.7 dBFS, tail DC 5.2e-04; {'loop_sat': 1}: peak -14.1 dBFS, tail DC 2.4e-04; {'converter': 1}: peak -13.8 dBFS, tail DC 4.4e-05; {'waveform': 1, 'intensity': 10, 'frequency': 10}: peak -13.8 dBFS, tail DC 2.6e-04; {'out_mode': 3, 'waveform': 2, 'intensity': 10, 'frequency': 8}: peak -13.8 dBFS, tail DC 2.7e-03 | bounded (wet <= -13 dBFS at unity output), finite, no DC build-up |
| 27 | parameter changes during active playback | PASS | per-vector random automation 20 s: finite=True, peak -5.2 dBFS, bounds errors 0; ramp feedback 0->9: 0.15x; ramp balance 0->10: 1.01x; ramp intensity 0->10: 1.10x; ramp in_level 2->8: 0.55x; ramp drive 0->24: 1.09x; ramp width 0->2: 0.99x; ramp out_gain -24->12: 0.92x | stable under per-vector automation; smoothed ramps click-free |
| 28 | TRUE STEREO channel isolation | PASS | WAVE TRI: R->L -240 dB (rounding only), L->R with silent R: -240 dB (rounding only); WAVE SQR: R->L -240 dB (rounding only), L->R with silent R: -240 dB (rounding only); WAVE RND: R->L -240 dB (rounding only), L->R with silent R: -240 dB (rounding only); WAVE ENV: L and R share one envelope/clock by design (coupled only when INTENSITY > 0) | independent L/R audio paths; one shared memory clock (as one hardware unit) |
| 29 | HOLD engage transition | PASS | T=5 ms: 1.00x; T=120 ms: 1.00x; T=380 ms: 0.73x; T=1008 ms: 1.09x; T=1023 ms: 0.83x | click-free engage (3rd-difference within 2.5x) |
| 30 | BYPASS transitions and residual wet signal | PASS | wet residual after BYPASS on: 50 ms -43 dBFS, 100 ms -72 dBFS, 150 ms -101 dBFS, 300 ms -192 dBFS; BYPASS on during playback: 0.76x; BYPASS off during playback: 0.01x; after >1.023 s bypassed, release outputs no stale echo (peak -240 dBFS) | 15 ms wet fade; converter input grounded; click-free on/off |
| 31 | host sample-rate change (state kept) | PASS | 48000->96000 Hz without reset: delay 250.012 ms, finite=True; 96000->44100 Hz without reset: delay 250.017 ms, finite=True; 44100->192000 Hz without reset: delay 250.010 ms, finite=True; 192000->48000 Hz without reset: delay 250.017 ms, finite=True | rate-dependent coefficients recomputed (cached on 'sr != h_sr') |
| 32 | memory / buffer boundary safety | PASS | 44100 Hz {'time_ms': 1023, 'waveform': 1, 'intensity': 10, 'frequency': 10}: 30 s, memory wraps ~58x, bounds errors 0, finite=True; 192000 Hz {'time_ms': 0, 'waveform': 0, 'intensity': 10, 'frequency': 10}: 30 s, memory wraps ~58x, bounds errors 0, finite=True; 22050 Hz {'time_ms': 1023, 'waveform': 1, 'intensity': 10, 'frequency': 10}: 30 s, memory wraps ~58x, bounds errors 0, finite=True; 48000 Hz {'time_ms': 1023, 'time_glide': 1, 'time_mode': 1}: 30 s, memory wraps ~29x, bounds errors 0, finite=True; 48000 Hz {'time_ms': 0, 'hold': 1}: 30 s, memory wraps ~29x, bounds errors 0, finite=True | every peek/poke index inside the 65536 x 2 Data (checked on every access) |
| 33 | out-of-range parameter values | PASS | values far outside the range are clamped to min/max (harness mirrors gen~ Param min/max); output finite | Param min/max |
| 34 | huge finite input sample (1e30) | PASS | output stays finite and below the ceiling (peak -1.8 dBFS), recovers |  |
| 35 | non-finite audio input (NaN / +inf / -inf) | PASS | single NaN: all outputs finite, level after 1.4 s within 0.00 dB of clean; single +inf: all outputs finite, level after 1.4 s within 0.00 dB of clean; single -inf: all outputs finite, level after 1.4 s within 0.00 dB of clean; 1000 NaN samples: all outputs finite, level after 1.4 s within 0.00 dB of clean; 1000 alternating +-inf/NaN: all outputs finite, level after 1.4 s within 0.32 dB of clean; invalid input during HOLD leaves the loop bit-identical: True | v1.0.2: invalid samples cannot contaminate memory, feedback or filter state; no reload needed |
| 36 | NaN parameter values (C model) | PASS | 23 parameters set to NaN for 0.3 s then restored: output finite throughout and audio resumes; failures: none. Whether gen~ Param clamping lets NaN through is NOT VERIFIED. |  |
| 37 | HOLD release transition | PASS | 108 cases (12 delay times x 44.1/48/96 kHz x MONO/TRUE STEREO, per channel, -6 dB input): output identical (-180 dB) to 'HOLD kept' until one delay time after release, or until ~944 ms for longer delays (worst early deviation 0.000 ms); worst click excess (>5 kHz, absolute AND level-relative) over both references +1.2 dB (limit +3) / metric sensitivity check, v1.0.1 engine on the same test: T=120: +27.0 dB, T=1008: +34.6 dB (flagged) / after T+80 ms the output equals the never-held output (FB 0): T=5@48000: -240 dB, T=380@48000: -240 dB, T=1023@48000: -240 dB, T=120@96000: -240 dB, T=700@44100: -240 dB / special cases (level-relative >5 kHz excess over both references): modulation TRI INT 3 T=380@48000: -4.8 dB; modulation TRI INT 3 T=1008@44100: -0.0 dB; modulation SQR INT 10 T=380@48000: -8.3 dB; modulation SQR INT 10 T=1008@44100: -7.6 dB; GLIDE + CONT T=380@48000: -4.7 dB; GLIDE + CONT T=1008@44100: +0.0 dB; FEEDBACK 9 + INV + LOW/HIGH T=380@48000: -8.2 dB; FEEDBACK 9 + INV + LOW/HIGH T=1008@44100: -1.2 dB; hold 6 s (seam crossed 6x) T=380@48000: -5.2 dB; hold 6 s (seam crossed 6x) T=1008@44100: -0.5 dB; release 2 ms after engage T=380@48000: -3.0 dB; release 2 ms after engage T=1008@44100: +0.0 dB; re-engage half-way through the release window T=380@48000: +0.0 dB; re-engage half-way through the release window T=1008@44100: -1.4 dB; time change during the release window T=380@48000: -4.0 dB; time change during the release window T=1008@44100: -1.3 dB; re-engage 4 ms into the 10 ms release fade T=380@48000: +0.0 dB; re-engage 4 ms into the 10 ms release fade T=1008@44100: -1.4 dB / full nominal level TRUE STEREO T=120: switchover window excess +1.1 dB (later content may overload the 13-bit converter, as the hardware would) | v1.0.2: loop keeps playing until the normal tap reads only new audio, then a 10 ms crossfade; no added latency; normal operation resumes |
| 38 | HOLD re-engaged shortly after a completed release | PASS | T=5 gap 50 ms: step 1.03x / spike 11.9 dB (first-ever HOLD 1.01x / 12.9 dB; v1.0.1 4.50x / 37.7 dB); T=16 gap 100 ms: step 1.13x / spike 12.9 dB (first-ever HOLD 1.19x / 13.3 dB; v1.0.1 2.84x / 37.0 dB); T=50 gap 50 ms: step 1.00x / spike 11.5 dB (first-ever HOLD 1.01x / 9.4 dB; v1.0.1 4.13x / 37.5 dB); T=120 gap 200 ms: step 1.03x / spike 6.3 dB (first-ever HOLD 1.00x / 7.7 dB; v1.0.1 3.28x / 38.2 dB); T=250 gap 600 ms: step 1.02x / spike 17.4 dB (first-ever HOLD 1.41x / 19.1 dB; v1.0.1 4.17x / 38.3 dB); T=380 gap 400 ms: step 1.01x / spike 5.2 dB (first-ever HOLD 1.02x / 11.6 dB; v1.0.1 2.49x / 34.1 dB); T=700 gap 300 ms: step 1.05x / spike 5.2 dB (first-ever HOLD 1.00x / 3.0 dB; v1.0.1 4.12x / 38.4 dB); T=900 gap 100 ms: step 1.07x / spike 7.0 dB (first-ever HOLD 1.01x / 3.3 dB; v1.0.1 4.20x / 39.8 dB); T=1023 gap 200 ms: step 1.11x / spike 13.6 dB (first-ever HOLD 1.14x / 14.4 dB; v1.0.1 2.41x / 34.6 dB) | re-captured loop as clean as a first-ever HOLD: worst step <= max(1.5x, 1.2x reference), recurring >5 kHz spike <= reference + 6 dB |
| 39 | A/B regression v1.0.2 vs v1.0.1 (identical input and settings) | PASS | 47 scenarios (9 programs x 4 output modes, 5 host rates, PRE on/off, clean/13-bit, extremes, HOLD engage, BYPASS, random automation): 47 bit-identical (all 5 outputs incl. meters/display) / intentional difference 1 (HOLD release): T=120: v1.0.1 worst step 10.1x -> v1.0.2 1.37x; T=1008: v1.0.1 worst step 21.3x -> v1.0.2 1.00x / intentional difference 2 (invalid input): v1.0.1 output finite=False, v1.0.2 output finite=True | bit-identical everywhere except HOLD release and invalid-input handling |
| 40 | processing latency | PASS | 44100 Hz: direct path 0 samples; effect path at TIME 0 = 0.022 ms (1.0 samples, filter group delay); 48000 Hz: direct path 0 samples; effect path at TIME 0 = 0.022 ms (1.0 samples, filter group delay); 96000 Hz: direct path 0 samples; effect path at TIME 0 = 0.030 ms (2.9 samples, filter group delay). No look-ahead or internal buffering; the device reports 0 latency to Live (patcher 'latency': 0). | direct path 0 samples |
| 41 | CPU of the C build per host rate (stereo, modulation on) | PASS | 44100 Hz: 20x real-time (5.03% of one core); 48000 Hz: 18x real-time (5.70% of one core); 88200 Hz: 9x real-time (10.77% of one core); 96000 Hz: 9x real-time (11.06% of one core); 192000 Hz: 4x real-time (23.54% of one core). Standalone benchmark of the translated gen~ code incl. Python block overhead; NOT a measurement inside Ableton Live. | informational |
| 42 | dry/wet balance law | PASS | BALANCE 0: dry 1.000 (exp 1.00), wet 0.000 (exp 0.00); BALANCE 2.5: dry 1.000 (exp 1.00), wet 0.495 (exp 0.50); BALANCE 5: dry 1.000 (exp 1.00), wet 0.990 (exp 1.00); BALANCE 7.5: dry 0.500 (exp 0.50), wet 0.990 (exp 1.00); BALANCE 10: dry 0.000 (exp 0.00), wet 0.990 (exp 1.00); WET ONLY: dry -240 dB | 0 = direct, 5 = 1:1, 10 = effect |
| 43 | start-up: no undelayed wet signal after instantiation | **FAIL** (known limitation) | fresh engine, effect only: output during the first 50 ms is -10.9 dB re input (identical in v1.0.1); exactly silent after 50 ms of settling |  |
| 44 | block-size independence (C harness) | PASS | block sizes 32: identical, 64: identical, 128: identical, 256: identical, 512: identical, 1024: identical, 2048: identical (parameter changes at block-aligned times, incl. HOLD) | no dependence on vector size |
| 45 | FB ROUTE INT: identical to rc3 and deaf to the return inputs | PASS | defaults: vs rc3 0e+00, with junk on return 0e+00; FB 10 + mod + filters: vs rc3 0e+00, with junk on return 0e+00; TRUE ST, HOLD engage: vs rc3 0e+00, with junk on return 0e+00 | default behaviour unchanged; return ignored unless EXT/BOTH |
| 46 | FB ROUTE EXT/BOTH: external loop regeneration | PASS | EXT RETURN 5: -3.01 dB/pass (INT FEEDBACK 5: -3.01, law -2.92); period 205.3 ms = TIME + routing latency; EXT unpatched: 2nd repeat -240 dB below the 1st (internal loop off); BOTH (FB 3 + RETURN 3): tail +5.1 dB vs INT FB 3 alone | EXT loop gain = RETURN/7 per pass; internal loop off in EXT, summed in BOTH |
| 47 | FB ROUTE: send tap, runaway bound, invalid return, mode switching | PASS | INT: send carries the echo (-7.4 dB re input burst); EXT RETURN 10 runaway: output peak -14.0 dBFS, send peak -14.0 dBFS (bounded); NaN/inf on the return (BOTH): outputs finite=True; INT->EXT->BOTH while playing: worst step 1.00x the steady-state step | send always active; bounded; NaN-safe; click-free switching |
| 48 | rc5: existing behaviour bit-identical to rc4 | PASS | INT defaults: 0e+00; EXT RETURN 6, loop 256: 0e+00; BOTH, FB 4: 0e+00; SYNC divisions 0-10: identical | LOOP COMP 0 / no CAL / old divisions change nothing |
| 49 | rc5: triplet divisions (1/16T, 1/32T appended; 1/8T unchanged) | PASS | 120 BPM div 11: 83.33 ms (expected 83.33); 120 BPM div 12: 41.67 ms (expected 41.67); 90 BPM div 11: 111.11 ms (expected 111.11); 120 BPM div 2: 166.67 ms (expected 166.67) | exact triplet times |
| 50 | rc5: CAL measures the external loop's round trip | PASS | loop 256 smp (5.33 ms): CAL 5.33 ms; loop 2048 smp (42.67 ms): CAL 42.67 ms; loop busy, return -6 dB: CAL 10.67 ms (expected 10.67); nothing patched: result -1.0; main output during CAL: max step 0.0e+00 (click stays on outputs 3/4); INT: CAL ignored | exact to the sample; robust to loop audio and fader; no click on the main output |
| 51 | rc5: LOOP COMP puts external repeats back on time | PASS | LOOP COMP 0.00: repeat period 210.71 ms; LOOP COMP 10.67: repeat period 200.00 ms; INT with LOOP COMP 20: identical (not applied) | period = TIME |

## 2. Static device checks — PASS (static)

Inspection of `dist/ECHOLIVITY SDD-3000.amxd`; nothing was executed in Max or Live.

| Check | Status | Detail |
|---|---|---|
| container | PASS (static) | ampf/aaaa, meta, ptch length 523654 = file size - 32, NUL-terminated, JSON parses, amxdtype audio effect |
| gen~ code == src/gen/echolivity_core.genexpr | PASS (static) | 39477 chars, sha256 673f01ac1b240de3... |
| GenExpr subset rules (tools/gen2c.py) | PASS (static) | gen2c: 39 params, 119 histories, 320 locals, 8 outs -> /tmp/echolivity_check.c -- gen~ compilation itself NOT VERIFIED |
| parameter count | PASS (static) | 162 parameters: 42 automatable + 120 stored-only (program memory) |
| parameter names unique | PASS (static) | 162 unique long names |
| 'parameters' table matches objects | PASS (static) | 162 entries |
| initial values inside ranges / enum sizes | PASS (static) | all 158 OK |
| Push / Configure banks | PASS (static) | 4 banks of 8 slots, all names resolve or are '-' |
| controls -> gen~ Params (name, connection, range) | PASS (static) | 36 controls verified |
| gen~ Params without a panel control | PASS (static) | ['p_cal', 'p_hf_comp', 'p_tempo']: p_cal is sent by the CAL button (rc5), p_tempo is fed by live.observer, p_hf_comp is an internal engineering switch (default on) |
| tempo sync chain | PASS (static) | live.thisdevice -> 'path live_set' -> live.path -> live.observer('property tempo') -> p_tempo -> gen~ |
| audio routing incl. EXT loop (rc4) | PASS (static) | plugin~ 1 2 3 4 -> gen~ in1-4 (3/4 = EXT return); gen~ out1/2 -> plugout~ 1/2, out6/7 -> plugout~ 3/4 (EXT send) -- Live routing NOT VERIFIED |
| program memory: 10 slots x 12 fields, factory values, write & recall wiring | PASS (static) | 120 stored-only slots match presets/factory_programs.json; every slot is written by its gate outlet and recalls into its control |
| send/receive pairs | PASS (static) | ['---edit', '---editclr', '---recall', '---ropen', '---wbang', '---write', '---wslot'] |
| initialisation pushes every stored control value to gen~ | PASS (static) | live.thisdevice -> [t b b b b b]: outlet 2 bangs 38 objects; momentary buttons deliberately excluded |
| LFO Mod mapping: Modulation Mode Additive on all continuous dials only | PASS (static) | 14 continuous controls (13 dials + RETURN) with parameter_modmode 3; enum/stored-only: none -- Live behaviour NOT VERIFIED |
| D-1: program logic closed during the start-up sequence; Program recalled first | PASS (static) | [t b b b b b] outlet 3 -> '0' -> [gate 1] (before outlet 2 re-outputs Program), outlet 0 -> '1'; Program parameter_order 0, other 161 parameters order 1 -- Live behaviour NOT VERIFIED |
| UI-1: backing panels in the background layer, LEDs/segments in front | PASS (static) | 20 static panels background 1; 43 driven panels foreground -- confirmed visually in Live 12 by the owner |
| presentation layout | PASS (static) | 42 controls inside 169 px, no overlapping controls |
| distributed .amxd == fresh build from source | PASS (static) | sha256 6129b1d209dea14464481a01885471dd63dff62bc7ffd2d6671b9b1952b9f65b |

## 3. Runtime integration in Ableton Live — BLOCKED (not executed)

Step-by-step procedures and pass criteria: `docs/LIVE_VALIDATION_CHECKLIST.md`.

No Max or Live installation was available, so none of the following has been observed running. The right-hand column shows only the static evidence that exists.

| Item | Status | Static evidence only |
|---|---|---|
| L-1 Device loading and gen~ compilation | BLOCKED | container/JSON checked; GenExpr subset rules; code identical to tested source |
| L-2 Audio input/output and stereo routing | BLOCKED | plugin~/gen~/plugout~ routing checked; engine output modes tested |
| L-3 Engine in Live matches the renders | BLOCKED | renders made by the tested engine |
| L-4 Parameter automation | BLOCKED | 158 definitions checked; engine automation and click tests PASS |
| L-5 MIDI mapping | BLOCKED | all 38 panel parameters are live.* parameters (mappable by design) |
| L-6 Tempo synchronisation and tempo automation | BLOCKED | live.observer chain checked; engine sync maths tested |
| L-7 Preset saving and recall, .adv persistence, programs / WRITE | BLOCKED | 120 stored-only slots + write/recall wiring checked |
| L-8 Project save / reopen | BLOCKED | init sequence wiring checked; engine starts without ramps |
| L-9 HOLD in Live | BLOCKED | engine HOLD tests PASS (engage, 108-case release matrix, re-engage) |
| L-10 BYPASS in Live | BLOCKED | engine BYPASS tests PASS |
| L-11 Sample-rate changes in Live | BLOCKED | engine rate-change test PASS (state kept) |
| L-12 Invalid-input recovery in Live (gen~ fixnan) | BLOCKED | engine NaN/Inf tests PASS in the C model |
| L-13 CPU in Live at 44.1-192 kHz | BLOCKED | C-build benchmark only (section 4) |
| L-14 Latency reported to Live / PDC | BLOCKED | patcher latency 0; engine direct path 0 samples |
| L-15 Interface appearance | BLOCKED | preview rendered from the same geometry, not by Max |

Suggested manual check: drag `audio_examples/00_dry_source.wav` onto a track, insert the device, step through programs 1–9 comparing with the matching renders, automate Delay Time / Feedback / High Cut / Hold, save and reopen the Set, save and load an .adv preset, and watch Live's CPU meter with 8 instances.

### Static-review risks (NOT VERIFIED, not changed)

These follow from the patch logic and depend on Live/Max runtime behaviour I could not observe. No change was made without reproducible evidence.
- **Re-selecting the active program** (including M) re-runs the recall. If `live.tab` re-outputs when the selected cell is clicked again, unsaved edits are discarded.
- **Loading an .adv preset onto a running device:** the Program parameter's change triggers a recall. If Live restores the Program parameter before the stored program slots, the recall can use the previous slot contents. Loading a Set is not affected: program logic stays disabled until `live.thisdevice` reports the device ready.
- **Automating Program** moves the stored controls. Any automation lanes on those controls will be overridden by Live, as with any device that sets its own parameters.

## 4. Performance and latency

### CPU (C build of the gen~ code — not inside Live)

| Host rate | v1.0.1 (% of one core) | v1.0.2-rc1 (% of one core) | change |
|---|---|---|---|
| 44100 Hz | 3.3 | 3.3 | +0% |
| 48000 Hz | 3.1 | 3.5 | +13% |
| 88200 Hz | 6.0 | 6.9 | +15% |
| 96000 Hz | 6.7 | 6.7 | +0% |
| 192000 Hz | 13.6 | 12.0 | -12% |

C build (`tests/bench_engine.c`), stereo, TRUE STEREO mode, TIME 380 ms, FEEDBACK 5, modulation on, 128-sample blocks, best of 3 runs, Intel Xeon 2.1 GHz shared VM (2 vCPU). Differences of this size are measurement noise on a shared VM. **This is not a measurement inside Ableton Live.**

### Latency

No look-ahead, no internal buffering; the patcher declares `latency: 0`. Measured (test 40): direct path 0 samples; effect path at TIME 0 = 1 sample (44.1/48 kHz) to 3 samples (96 kHz) of filter group delay. In Live: NOT VERIFIED (L-14).

### Standalone benchmark vs. Live

The benchmark runs the C translation of the same GenExpr with gcc -O2. In Live, gen~ generates and compiles its own code; Max adds scheduling and Live adds device overhead. Expect different absolute numbers. The relative statement (v1.0.2 costs the same as v1.0.1) is the meaningful result here.

## 5. Audio regression comparison (v1.0.1 vs v1.0.2-rc1, identical input and settings)

Click excess = dB by which the >5 kHz content exceeds the 'HOLD kept' and 'never held' references in both absolute and level-relative terms (the same metric as test 38).

| Regression pair (sustained chord, FB 4, effect only) | v1.0.1 | v1.0.2-rc1 |
|---|---|---|
| `hold_release_T380` | click excess +30.6 dB | click excess -0.5 dB |
| `hold_release_T1008` | click excess +29.8 dB | click excess -0.7 dB |
| `hold_release_then_reengage` | click excess +14.1 dB | click excess +0.2 dB |
| `invalid_input_nan_at_2s` (music, BALANCE 5) | output NaN from 2.0 s to the end (written as silence) | output continues normally (-20.9 dBFS RMS after the burst) |

All 19 v1.0.1 demo renders re-render **bit-identically** with v1.0.2-rc1. The engineering change report (`docs/ENGINEERING_CHANGES.md`) lists every intentional sonic difference.

## 6. Outstanding issues

See `docs/OUTSTANDING_ISSUES.md`.

## 7. Reproducibility

| Check | Status | Detail |
|---|---|---|
| no temporary or build files in the release tree | PASS | 117 files scanned; stray: none; local-only dirs excluded from the release: ['build'] |
| clean checkout prepared | PASS | 117 files copied to an empty directory, no build/ directory |
| clean rebuild reproduces the shipped artefacts | PASS | src/gen/echolivity_core.genexpr: 673f01ac1b240de3...; src/max/ECHOLIVITY_SDD-3000.maxpat: d0ce9bb4090537ce...; dist/ECHOLIVITY SDD-3000.amxd: 6129b1d209dea144...; docs/ui_preview.png: 8be4e65ebd0ba6de... |
| deterministic build (two consecutive builds identical) | PASS | 4 artefacts compared |
| engine tests pass from the clean checkout | PASS | exit 0; 50/51 PASS, 1 known-limitation FAIL; results identical to the release tree: True |
| static device checks pass from the clean checkout | PASS | 20/20 |
| audio examples re-render identically from the current DSP | PASS | 27 WAV files (1 dry source + 26 renders) |
| unchanged versus baseline rc4_unchanged_in_rc5.sha256 | PASS | presets/factory_programs.json: identical; tools/hfcomp_table.json: identical; audio_examples/00_dry_source.wav: identical; audio_examples/01_classic_echo.wav: identical; audio_examples/02_short_slap.wav: identical; audio_examples/03_dub_regeneration_sync.wav: identical; audio_examples/04_metallic_flange.wav: identical; audio_examples/05_wide_doubling_stereoA.wav: identical; audio_examples/06_vibrato.wav: identical; audio_examples/07_random_drift.wav: identical; audio_examples/08_infinite_hold_then_play_over.wav: identical; audio_examples/09_rhythmic_modulation_square.wav: identical; audio_examples/10_filters_in_loop_LOW500_HIGH2k.wav: identical; audio_examples/11_regen_invert_flange_compare.wav: identical; audio_examples/12_envelope_doppler.wav: identical; audio_examples/13_preamp_crunch_minus10_delay_bypassed.wav: identical; audio_examples/14a_converter_13bit_quiet_tail.wav: identical; audio_examples/14b_converter_clean_quiet_tail.wav: identical; audio_examples/15_stereoB_plus_minus_mix.wav: identical; audio_examples/16_self_oscillation_bounded.wav: identical; audio_examples/17_time_change_glide.wav: identical; audio_examples/regression/hold_release_T1008_v1.0.1.wav: identical; audio_examples/regression/hold_release_T1008_v1.0.2.wav: identical; audio_examples/regression/hold_release_T380_v1.0.1.wav: identical; audio_examples/regression/hold_release_T380_v1.0.2.wav: identical; audio_examples/regression/hold_release_then_reengage_v1.0.1.wav: identical; audio_examples/regression/hold_release_then_reengage_v1.0.2.wav: identical; audio_examples/regression/invalid_input_nan_at_2s_v1.0.1.wav: identical; audio_examples/regression/invalid_input_nan_at_2s_v1.0.2.wav: identical; audio_examples/musical_eval/10_ext_loop_rimshot_latency256.flac: identical; audio_examples/musical_eval/10_int_loop_rimshot_reference.flac: identical; audio_examples/musical_eval/1_rimshot__conservative.flac: identical; audio_examples/musical_eval/1_rimshot__dark_long.flac: identical; audio_examples/musical_eval/1_rimshot__dry.flac: identical; audio_examples/musical_eval/1_rimshot__dub_throw.flac: identical; audio_examples/musical_eval/2_kick_snare__conservative.flac: identical; audio_examples/musical_eval/2_kick_snare__dry.flac: identical; audio_examples/musical_eval/2_kick_snare__dub_throw.flac: identical; audio_examples/musical_eval/3_dub_bass__conservative.flac: identical; audio_examples/musical_eval/3_dub_bass__dry.flac: identical; audio_examples/musical_eval/3_dub_bass__dub_throw.flac: identical; audio_examples/musical_eval/4_organ_skank__conservative.flac: identical; audio_examples/musical_eval/4_organ_skank__dark_long.flac: identical; audio_examples/musical_eval/4_organ_skank__dry.flac: identical; audio_examples/musical_eval/4_organ_skank__dub_throw.flac: identical; audio_examples/musical_eval/5a_spring_send__conservative.flac: identical; audio_examples/musical_eval/5a_spring_send__dark_long.flac: identical; audio_examples/musical_eval/5a_spring_send__dry.flac: identical; audio_examples/musical_eval/5a_spring_send__dub_throw.flac: identical; audio_examples/musical_eval/5b_plate_send__conservative.flac: identical; audio_examples/musical_eval/5b_plate_send__dry.flac: identical; audio_examples/musical_eval/5b_plate_send__dub_throw.flac: identical; audio_examples/musical_eval/6_dense_mix__conservative.flac: identical; audio_examples/musical_eval/6_dense_mix__dry.flac: identical; audio_examples/musical_eval/6_dense_mix__dub_throw.flac: identical; audio_examples/musical_eval/6_dense_mix__extreme_soft_fb9.flac: identical; audio_examples/musical_eval/7_ride_fb_4-10-5_hard.flac: identical; audio_examples/musical_eval/7_ride_fb_4-10-5_hard_filtered.flac: identical; audio_examples/musical_eval/7_ride_fb_4-10-5_soft.flac: identical; audio_examples/musical_eval/7_ride_fb_4-10-5_soft_filtered.flac: identical; audio_examples/musical_eval/8_long_evolving_fb8_soft_rnd_highsweep.flac: identical; audio_examples/musical_eval/9_desk_drive_snare_+4dBFS.flac: identical; audio_examples/musical_eval/9_desk_drive_snare_-17dBFS.flac: identical; audio_examples/musical_eval/9_desk_drive_snare_0dBFS.flac: identical |

Checksums of every shipped file: `SHA256SUMS.txt`.

## 8. Output protection

Measured curves and the distinction from a 0 dBFS limiter: `docs/OUTPUT_PROTECTION.md`.

## 9. Audio examples

`audio_examples/` contains 19 WAV files (48 kHz, 16-bit stereo): the dry source plus 18 renders made by the tested engine. They re-render bit-identically from the v1.0.1 source (section 5).

- `00_dry_source.wav`
- `01_classic_echo.wav`
- `02_short_slap.wav`
- `03_dub_regeneration_sync.wav`
- `04_metallic_flange.wav`
- `05_wide_doubling_stereoA.wav`
- `06_vibrato.wav`
- `07_random_drift.wav`
- `08_infinite_hold_then_play_over.wav`
- `09_rhythmic_modulation_square.wav`
- `10_filters_in_loop_LOW500_HIGH2k.wav`
- `11_regen_invert_flange_compare.wav`
- `12_envelope_doppler.wav`
- `13_preamp_crunch_minus10_delay_bypassed.wav`
- `14a_converter_13bit_quiet_tail.wav`
- `14b_converter_clean_quiet_tail.wav`
- `15_stereoB_plus_minus_mix.wav`
- `16_self_oscillation_bounded.wav`
- `17_time_change_glide.wav`

`audio_examples/regression/` (8 files, v1.0.1 vs v1.0.2-rc1, see section 5):

- `regression/hold_release_T1008_v1.0.1.wav`
- `regression/hold_release_T1008_v1.0.2.wav`
- `regression/hold_release_T380_v1.0.1.wav`
- `regression/hold_release_T380_v1.0.2.wav`
- `regression/hold_release_then_reengage_v1.0.1.wav`
- `regression/hold_release_then_reengage_v1.0.2.wav`
- `regression/invalid_input_nan_at_2s_v1.0.1.wav`
- `regression/invalid_input_nan_at_2s_v1.0.2.wav`

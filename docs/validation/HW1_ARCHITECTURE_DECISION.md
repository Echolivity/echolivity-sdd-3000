# HW-1 Remediation — Architecture Decision

Baseline: `16d87a7` (HW-1 root-cause investigation). Status: **decision for the experimental candidate only.** The production DSP, the device, the presets and the release status are unchanged.

All figures come from C builds of the gen~ code (`tools/gen2c.py`) or from the isolated conversion model (`experiments/hw1/convmodel.py`). Nothing in this document was measured in Max 9 or Live 12, or on original hardware.

## 1. Problem

The investigation found the cause of HW-1. The 64 kHz memory clock is converted from and to the host rate with two short kernels:

- linear interpolation on the input side;
- a box-integrated zero-order hold (ZOH) on the output side.

Neither kernel rejects images, so the images fold into the audio band (−8 to −18 dB re tone at 17–20 kHz).

The previous recommendation, candidate B (32-tap linear-phase windowed sinc), removed the spurs. It failed on timing:

- **0.5 ms latency** at TIME 0;
- 21 of the 51 existing tests failed;
- 1.7–1.9× CPU.

The brief rules out trading delay timing for spectra.

## 2. Architectures evaluated

Isolated model with the quantiser off, sweep 100 Hz–20 kHz. Source: `experiments/hw1/results/latency_alternatives.json` and `latency_alternatives.png`.

| Architecture | Worst spur 44.1 / 48 / 96 kHz | Core latency at 1 kHz | Group delay at 17 kHz | 17 kHz core response (48 kHz) | Modulated 17 kHz spill | Rough MACs per sample |
|---|---|---|---|---|---|---|
| Production (linear in, ZOH box out) | −17.6 / −11.9 / −8.2 dB | 0.003 ms | 0 | −5.33 dB | −16 dB | 5 |
| B, linear-phase sinc, 32 taps | −115 / −118 / −106 | 0.667 ms | 0.667 ms | −0.54 | −127 | 256 |
| B, 16 taps | −106 / −102 / −106 | 0.333 ms | 0.333 ms | −3.49 | −116 | 128 |
| B, 12 taps (fixed count) | −108 / −98 / **−51** | 0.25 ms | 0.25 ms | −4.97 | −111 | 96 |
| Minimum-phase FIR, 16 taps | −51 / −44 / −41 | 0.056 ms | 0.096 ms | −1.76 | −51 | 128 |
| **D**, 5th-order elliptic + 1 pole | −49 / −50 / −55 | 0.063 ms | 0.085 ms | −2.09 | −57 | ~93 |
| **D, 7th-order elliptic 21 kHz + poles at 50/70 kHz (chosen)** | **−92 / −94 / −101** | **0.091 ms** | 0.131 ms | −2.46 | **−92** | ~140 |
| D, 9th-order elliptic | −100 / −96 / −98 | 0.105 ms | 0.174 ms | −1.78 | −100 | ~140 |
| Short path using low-order D filters (3rd-order elliptic, Butterworth or Bessel) | −2 to −18 (worse than production) | 0.036–0.042 ms | — | — | — | — |

Notes on the table:

- **Short-delay path:** low-order filters lose the sinc nulls of the ZOH box, which is why they do worse than production.
- **Linear-phase FIRs (B):** they need about L/2 of latency on each side. At a fixed tap count they fail at 96 kHz. At a fixed duration they cost more CPU at high rates.
- **Minimum-phase FIR:** has low latency, but the truncated minimum-phase kernel gives poor rejection.
- **D, an analog-prototype filter evaluated exactly in continuous time:**
  - It treats both conversions as what the hardware had: an analog anti-alias low-pass in front of the ADC, and the ZOH DAC staircase through an analog reconstruction low-pass.
  - Each filter is a sum of complex one-pole terms, `H(s) = Σ rᵢ/(s − pᵢ)`.
  - Input side: one host-rate state per pole, read out exactly at each tick as `x(t_k) = Σ Re(sᵢ·e^{pᵢτ})`.
  - Output side: every staircase step adds `Δq·(rᵢ/pᵢ)·e^{pᵢ(n−t_k)}` to a host-rate state.
  - It is exact for any tick times, so a modulated clock is handled natively.
  - Cost is O(order) per tick: no kernel table, no look-ahead, no allocation.
  - Latency is the filters' own group delay (tens of microseconds), not half a FIR.
  - Its passband ends at 21 kHz and its stopband (−90 dB) starts at about 43 kHz. That is enough because only images in 64 kHz ± 20 kHz fold into the audio band. Images that stay below 32 kHz fold back onto the tone itself (a response effect, not a spur).
- **Extra poles at 50 and 70 kHz:** a strictly proper elliptic filter falls at only 20 dB/decade above its last zero, and the impulse-train input adds up every far image. Two real poles cost 5 µs and lower the floor from −77 to −94 dB.

## 3. The TIME-0 problem, and how it is solved

Whatever its order, D adds about 0.09 ms of group delay, and a causal filter cannot get rid of it. The existing tests require:

- an effect-path latency at TIME 0 below 0.05 ms;
- every delay accurate to within 30 µs of the TIME-0 baseline.

The chosen design meets both without sacrificing timing:

- **TIME ≥ 1 ms (memory path):**
  - The analog-pair latency is subtracted from the read offset in whole memory ticks: 6 ticks at every calibrated rate.
  - Whole ticks keep `fa = 0`, so there is no new fractional-read interpolation loss in the loop.
  - The echo lands at the same constant latency as TIME 0, with a residual of 0.3–2.7 µs.
- **TIME 0 (error-feedforward short path):**
  - The wet signal is the converter input through a matched host-rate biquad M (magnitude error ≤ 0.12 dB).
  - The converter's own error (quantisation, gain ranging, clipping) is added on top. It is computed on a host-aligned copy of the input and held/box-integrated as in production.
  - The signal itself never passes a resampler, so there are no images and no added latency.
  - Overload compresses exactly as on the memory path (within 0.01 dB from +8.5 to +9.75 dBm).
  - The 13-bit error staircase matches the memory path within 0.2 dB.
- **Switching:**
  - The short path is used only when the target delay is 0 (TIME 0, or continuous TIME below 0.094 ms).
  - It is selected only after a tap crossfade has settled, and never while HOLD plays the memory.
  - It crossfades over 10 ms with a smoothstep.
  - TIME 0↔1 ms and 0↔380 ms switches measure 0.76–1.0× on the click metric (production 0.70–1.0×).

## 4. Preserving the voicing

D has much less top-octave droop than production, so production's droop EQ would over-brighten it. The EQ is refitted to match **production's measured tone response**, not a flatter one:

- Two RBJ peaking sections per rate range; the first reuses production's structure.
- The fit uses least-squares single-tone fits, not noise.
- The fit is within 0.04 dB of production from 300 Hz to 19 kHz, except near 17 kHz (see the next point).
- It is held inside the service-manual band (20 Hz–17 kHz, +0.5/−3 dB). Production's *tone* response at 17 kHz is −3.35 dB (48 kHz) and −3.08 dB (96 kHz), so production itself is out of spec. Its own test reads −2.86 dB only because the rms includes image energy. The candidate is −2.76 to −2.86 dB at every rate, about +0.6 dB above production at 17 kHz at 48 kHz.
- No EQ boost is allowed above 21 kHz, which keeps the ultrasonic loop gain at or below D's own.

A finding on the way: production's droop-EQ table (`tools/hfcomp_table.json`) was fitted from a noise/cross-spectrum (CSD) estimate. That estimate is biased by the very images HW-1 is about: on production it reads +0.5 dB at 200 Hz where a sine reads +0.1 dB. This is why production misses its own −3 dB target at 17 kHz.

## 5. Decision

**Candidate D is the remediation architecture.** It is the only option evaluated that does all of the following at once:

- rejects the conversion images by 80–117 dB at every rate and with a modulated clock;
- keeps the existing timing contract: TIME 0 below 0.05 ms, every delay within 30 µs of TIME 0, LOOP COMP and tempo sync exact;
- costs 1.25× production CPU (median), against 1.7–1.9× for B.

This is an engineering decision. It does **not** approve a production change. Production approval depends on the gates in `HW1_REMEDIATION_REPORT.md`, and the native Max 9 / Live 12 gate has not been run.

Rejected alternatives:

- **B (any tap count):** fails the TIME-0 latency and delay-relative criteria, and at a fixed tap count it fails 96 kHz.
- **Minimum-phase FIR:** rejection −41 to −51 dB.
- **Low-order D, and a "production conversion at TIME 0" short path:** HW-1 would remain at TIME 0.
- **C (×4 oversampling, from the investigation):** fails at 44.1 and 96 kHz.

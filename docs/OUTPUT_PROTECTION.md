# Output protection — what it actually does

*v1.0.1 documentation of the unchanged v1.0 DSP. Measured with `tools/analyse_output_protection.py`.*

**Summary:** ECHOLIVITY has **no 0 dBFS brick-wall limiter**. It has two *memoryless soft-saturation curves* (instantaneous waveshapers). Neither has look-ahead, attack/release or a gain-reduction envelope, and both add harmonic distortion when driven.

| Stage | Formula (`v` = linear sample, 1.0 = 0 dBFS) | Active | Asymptote |
|---|---|---|---|
| Output-amp curve (part of the preamp *character*) | `v / (1 + |v|^5)^(1/5)`, applied **before** OUT ATT and OUT GAIN | blended in with **PRE** | 1.0 × OUT ATT × OUT GAIN (= 0 dBFS at +4 / 0 dB) |
| Safety ceiling (engineering safeguard) | `v / (1 + (|v|/4)^8)^(1/8)`, applied **last** | always | 4.0 = **+12.04 dBFS**, approached but never reached |

## Curves

| Safety ceiling: input peak | output peak | gain change | THD (sine) |
|---|---|---|---|
| -6 dBFS | -6.00 dBFS | -0.000 dB | -171 dB |
| +0 dBFS | -0.00 dBFS | -0.000 dB | -123 dB |
| +3 dBFS | +3.00 dBFS | -0.000 dB | -99 dB |
| +6 dBFS | +6.00 dBFS | -0.004 dB | -75 dB |
| +9 dBFS | +8.94 dBFS | -0.064 dB | -52 dB |
| +12 dBFS | +11.27 dBFS | -0.732 dB | -30 dB |
| +18 dBFS | +12.04 dBFS | -5.963 dB | -13 dB |
| +24 dBFS | +12.04 dBFS | -11.959 dB | -9 dB |
| +40 dBFS | +12.04 dBFS | -27.959 dB | -7 dB |

Asymptote: 4.0 = +12.04 dBFS (approached, never reached). Not a 0 dBFS limiter.

| Output-amp curve (PRE on, OUT ATT +4, GAIN 0 dB): input peak | output peak | gain change | THD (sine) |
|---|---|---|---|
| -6 dBFS | -6.05 dBFS | -0.054 dB | -54 dB |
| +0 dBFS | -1.20 dBFS | -1.204 dB | -27 dB |
| +3 dBFS | -0.28 dBFS | -3.284 dB | -18 dB |
| +6 dBFS | -0.05 dBFS | -6.054 dB | -14 dB |
| +9 dBFS | -0.01 dBFS | -9.010 dB | -11 dB |
| +12 dBFS | -0.00 dBFS | -12.002 dB | -10 dB |
| +18 dBFS | -0.00 dBFS | -18.000 dB | -8 dB |
| +24 dBFS | -0.00 dBFS | -24.000 dB | -7 dB |
| +40 dBFS | -0.00 dBFS | -40.000 dB | -7 dB |

Asymptote: 1.0 x OUT ATT x OUT GAIN (= 0 dBFS at +4 / 0 dB), then the safety ceiling.

| End-to-end (BALANCE 0, +4/+4) | input | output peak |
|---|---|---|
| PRE on, GAIN +0 dB | +0 dBFS | -1.91 dBFS |
| PRE on, GAIN +0 dB | +6 dBFS | -1.23 dBFS |
| PRE on, GAIN +0 dB | +12 dBFS | -1.20 dBFS |
| PRE on, GAIN +12 dB | +0 dBFS | +9.92 dBFS |
| PRE on, GAIN +12 dB | +6 dBFS | +10.48 dBFS |
| PRE on, GAIN +12 dB | +12 dBFS | +10.50 dBFS |
| PRE off, GAIN +0 dB | +0 dBFS | -0.00 dBFS |
| PRE off, GAIN +0 dB | +6 dBFS | +6.00 dBFS |
| PRE off, GAIN +0 dB | +12 dBFS | +11.27 dBFS |
| PRE off, GAIN +12 dB | +0 dBFS | +11.27 dBFS |
| PRE off, GAIN +12 dB | +6 dBFS | +12.04 dBFS |
| PRE off, GAIN +12 dB | +12 dBFS | +12.04 dBFS |

## What this means in practice

- **PRE on, OUT ATT +4, GAIN 0 dB (default):** peaks saturate softly toward 0 dBFS. The curve starts acting well below that (−0.05 dB at −6 dBFS, −1.2 dB at 0 dBFS). This is modelled analog character (the original's output amplifier clips at +21 dBm = 0 dBFS here), not a limiter.
- **PRE off, or OUT GAIN above 0 dB:** the output **can exceed 0 dBFS**, up to +12.04 dBFS. Live's float mixer carries this, but your master bus or converters may clip. Watch the track meter.
- The safety ceiling is bit-transparent to 0 dBFS and adds < 0.005 dB of gain change up to +6 dBFS. It exists only to stop extreme settings (−30 input range, LEVEL 10, +12 dB gain, character off) from producing very large values. v1.0's fuzz test reached +46 dBFS before it was added.
- Self-oscillating feedback is bounded separately, by the converter's full-scale clip inside the loop: the wet signal stays ≤ −13.7 dBFS at unity output settings in every tested combination.

## Correction to the v1.0 documentation

v1.0 said "a transparent safety ceiling keeps the output below +12 dBFS". More precisely, it is a soft curve whose asymptote is **+12.04 dBFS**. A +12 dBFS peak comes out at +11.27 dBFS (−0.73 dB, about −30 dB THD on a sine). It is not a brick-wall at +12 dBFS, and it is not a 0 dBFS protection.

## Input guard (v1.0.2)

At the input, NaN samples become 0 and ±inf become ±1000 (+60 dBFS). Finite input beyond ±1000 is clamped to ±1000. This is far above the clip point of every input range, so the result is the same saturated output as before. It is a robustness guard, not a limiter: valid audio below +60 dBFS is untouched (bit-identical).

## Possible future option (not implemented)

A conventional, switchable **0 dBFS true-peak limiter** (look-ahead, release, off by default) could be added in a future feature release. It would change gain staging and latency, so it was deliberately left out of the v1.0.1 hardening release.

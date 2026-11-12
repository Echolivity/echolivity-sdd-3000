# ECHOLIVITY SDD-3000 — Research notes: authentic vs. inferred vs. modern

ECHOLIVITY is an independent homage to the 1982 Korg SDD-3000 rack delay. It is not a Korg product and does not claim component-level accuracy. This file records where each behaviour comes from, in four categories that are kept separate throughout the documentation:

1. **Original hardware-derived behaviour** (section A): documented in Korg's service or owner's manual, or independently in period sources.
2. **Measured characteristics** (section A2): what ECHOLIVITY actually measures in the automated tests, compared with the documented specification.
3. **Engineering approximations and inferences** (section B): choices where documentation is missing, plus safeguards that the 1982 hardware did not need.
4. **Modern enhancements** (section C): optional features that did not exist on the original (blue "EXT" legends).

Approximations are approximations. Nothing in sections B or C should be read as exact hardware emulation.

## Sources (in order of authority)

| # | Source | Used for |
|---|--------|----------|
| SM | Korg SDD-3000 **Service Manual** (Keio Electronic Laboratory, 1982): spec sheet p.1, block diagram p.3, check & adjustment p.14–15 | Signal flow, specs, filter slopes, clock, LFO shapes, feedback behaviour |
| OM | SDD-3000 **Owner's Manual** (archive.org OCR) | Front-panel operation, HOLD/BYPASS/INV behaviour, outputs, program memory, application settings |
| EMM | *Electronics & Music Maker*, May 1983 review (muzines.co.uk) | Independent confirmation of specs and behaviour (random smoothing, HOLD, outputs) |
| VD | vintagedigital.com.au spec page | Confirmation of the headline specs |
| UAD | Universal Audio SDD-3000 plug-in manual | Input attenuator / preamp description (third-party emulation; not treated as authoritative) |
| PED | Korg SDD-3000 **Pedal** (2013) MIDI implementation | Filter frequencies (identical to SM) and sync division list |
| PARTS | syntaur.com parts list | 6012 12-bit DAC, LM393 comparator, 4558/TL072 op-amps |

## A. Authentic behaviour (documented)

| Behaviour | Value in ECHOLIVITY | Source |
|---|---|---|
| Delay range / step | 0–1023 ms, 1 ms steps | SM p.1, OM, EMM |
| Memory | 64K words (4864 = 65 536 × 1 DRAM); 1023 ms × 64 kHz = 65 472 words | SM p.6 reference data, SM p.15 |
| Sampling clock | 64 kHz nominal | SM p.15 §5 "Sampling Frequency 64 kHz ±2 kHz" |
| Modulation acts on the clock (VCO), not a read pointer | LFO → VCA → VCO → memory control logic | SM p.3 block diagram; SM p.15 §6 "MOD sampling frequency 40–78 kHz" |
| Modulation depth | INTENSITY 0–2:1; delay only gets shorter (100 % → 50 %) | SM p.1, OM, EMM |
| Rate | 0.1–15 Hz; FREQ 0 = 10 s period | SM p.1, SM p.14 §1 |
| Waveforms | Triangle, Square, Random, Envelope | SM p.1, OM |
| Triangle shape | sharp peak, rounded trough | SM p.14 Fig.3 |
| Random | per-cycle random level, "integrated" (smoothed); rate set by FREQUENCY | SM p.14 §3, OM, EMM ("natural at ~8 Hz") |
| Envelope | delay shortens as input rises; ≈2 s decay | OM, EMM, SM p.14 Fig.4 (decay to 25 % of swing in 2 s → τ ≈ 1.44 s) |
| Square = pitch-shifted echo / trills up to an octave | clock jumps up to 2:1 | OM, EMM |
| LOW cut | FLAT / 125 / 250 / 500 Hz, **−3 dB/oct** | SM p.1 (PED gives the same frequencies) |
| HIGH cut | FLAT / 8k / 4k / 2k Hz, −6 dB/oct | SM p.1 |
| Filters are after the memory, inside the regeneration loop | wet → LPF → de-emphasis → LOW → HIGH → (balance, feedback) | SM p.3 |
| Feedback summed in the analog domain before the converter | yes | SM p.3 |
| Feedback can self-oscillate | FB 10 @ 50 ms with 500 Hz/2 kHz filters oscillates; with no input it doesn't | SM p.15 §7 |
| "Above about 7 causes oscillation" | loop gain = FEEDBACK / 7 | OM application notes |
| Regeneration INV | inverts the feedback only | OM, SM p.15 §7.5 |
| Output INV | inverts the delayed signal at VARIABLE and +MIX only; not stored | OM |
| Outputs | VARIABLE (front), DIRECT, +MIX/MONO, −MIX | SM p.3, OM, EMM |
| Stereo A / Stereo B | DIRECT/+MIX and +MIX/−MIX | OM |
| HOLD | loops the last ~1 s indefinitely with no degradation; input locked out; time/feedback frozen; filters, INV and modulation still active | OM, EMM |
| BYPASS | all outputs direct; converter input grounded (clears a loop) | OM, SM p.3 |
| Input attenuator | −30 / −10 / +4 dBm; −30 adds a Hi-Z amplifier | SM p.1/p.3, UAD |
| Input clip | −13 / +7 / +21 dBm at LEVEL 5 | SM p.1 |
| Output attenuator | −20 / −10 / +4 dBm (clip −3 / +7 / +21 dBm) | SM p.1 |
| Headroom meter | −20…0 dB in 5 dB steps + red +3 dB; reads input **plus feedback** | OM, EMM, SM p.3 |
| Balance | 0 = direct, 10 = effect, continuous | OM |
| Effect frequency response | 20 Hz–17 kHz +0.5/−3 dB | SM p.1 |
| Converter | 12-bit DAC + gain-ranging ("12-bit plus one" = 13-bit), no compander breathing | PARTS, UAD, SM p.3 (real-time attenuator), SM p.14 "compander" trim, EMM |
| Pre-/de-emphasis around the converter | yes | SM p.3 |
| Programs | 9 + manual (0); stores delay time + regeneration + modulation + effect; HOLD & Output INV not stored; decimal point marks an edited program | OM, EMM |

## A2. Measured characteristics (ECHOLIVITY vs. the documented spec)

From `docs/TEST_REPORT.md` (C build of the exact gen~ code; not measured on the hardware):

| Characteristic | Spec / source | ECHOLIVITY measured |
|---|---|---|
| Delay time, 1–1023 ms | 1 ms steps (SM) | within 7 µs at 44.1–192 kHz |
| Effect response | 20 Hz–17 kHz +0.5/−3 dB (SM) | −0.26 dB @ 20 Hz … −2.86 dB @ 17 kHz (48 kHz host) |
| HIGH cut −3 dB points | 8k / 4k / 2k (SM) | −3.01 / −2.97 / −2.97 dB at fc |
| LOW cut slope | −3 dB/oct (SM) | 2.84–2.92 dB/oct below fc |
| Modulation depth at INTENSITY 10 | 2:1 (SM, OM) | 50.0 % of the displayed time |
| Rate range | 0.1–15 Hz (SM) | 0.100–15.000 Hz |
| Envelope decay | ≈2 s (SM Fig.4) | τ = 1.44 s |
| Input clip at LEVEL 5 | −13 / +7 / +21 dBm (SM) | 1 dB compression at −13.5 / +6.5 / +20.5 dBm |
| FB 10, 50 ms, 500 Hz/2 kHz | oscillates; silent with no input (SM 7.7) | oscillates at −18 dBFS; output exactly 0 with LEVEL 0 |

## B. Engineering approximations and informed inferences

| Item | ECHOLIVITY choice | Why |
|---|---|---|
| Clock range | 64 kHz → up to 128 kHz (2:1) | The service manual sweeps 40–78 kHz (also 2:1), which implies the CPU rescales the address offset when modulating. Expected to make no audible difference below 17 kHz (inferred; not compared against hardware). Documented as a simplification. |
| Gain-ranging threshold | ±0.5 FS, 6 dB step, instantaneous | "12-bit plus one" plus the SM trim of the switching "gap". Exact threshold unknown. |
| Emphasis time constants | 50 µs / 15 µs shelf (+10.5 dB HF) | The SM shows pre/de-emphasis blocks but no values; 50/15 µs is the period standard. |
| −3 dB/oct LOW cut | three pole/zero pairs two octaves apart (half-order approximation); alternative −6 dB/oct switch | The SM states −3 dB/oct. That's unusual and could be a typo, so both are offered. |
| AA / reconstruction filters | 2-pole + 2-pole, corners chosen to give −3 dB @ 17 kHz together with the 64 kHz ZOH | Meets the SM response spec. |
| FREQUENCY knob law | exponential 0.1 × 150^(k/10) Hz | Endpoints from the SM; law inferred. The owner's-manual chart values (FREQ 2–3 for chorus/flange) fall at sensible rates. |
| LEVEL taper | (L/5)² → 0 dB at 5, +12 dB at 10 | 5 is the SM reference point; the curve is assumed. |
| Balance law | dry = min(1,(10−B)/5), wet = min(1,B/5) (1:1 at centre) | UAD states 1:1 at the centre; the exact law is assumed. |
| Preamp clipping | op-amp-style rail clip (JRC4558 / TL072 per parts list); clip points match the SM | Character approximation, not a circuit model. |
| Envelope attack | 2 ms | Not documented. |
| Hold loop length | 1008 ms (64 512 words) with a 16 ms seam crossfade | Original ≈1.02 s; the crossfade removes the seam click the brief forbids. |
| Host-rate droop compensation | one RBJ peaking EQ per host rate (`tools/hfcomp_table.json`) | Emulating a 64 kHz clock inside a 44.1–192 kHz host adds interpolation/averaging losses (−7 dB @ 17 kHz at 44.1 kHz) that the hardware does not have; the EQ restores the documented response. An engineering correction, not a sound choice. |
| Time-change crossfade (XFADE) | 25 ms equal-power crossfade between two memory taps | The original jumped addresses (audible clicks); the brief requires click-free changes. |
| Load behaviour | smoothers start at the stored values | Prevents parameter ramps when a Set loads. |
| HOLD release (v1.0.2) | loop keeps playing until the normal tap reads only new audio, writer restarts behind the HOLD reader, 10 ms smoothstep crossfade; loop fades early above ~944 ms | The original's transition after HOLD is undocumented; the hardware most likely jumped addresses (audible). The brief requires click-free transitions. Engineering choice, not a hardware claim. |
| Invalid-input guard (v1.0.2) | NaN → 0, ±inf → ±1000 at the input; all states and memory writes NaN-guarded | Software-only hazard (the hardware's analog input cannot carry NaN); bit-identical for valid audio. |
| Output safety ceiling | soft curve, asymptote +12.04 dBFS (`docs/OUTPUT_PROTECTION.md`) | Safeguard against extreme gain settings; not a 0 dBFS limiter. |
| Panel colour | charcoal/black (brief) | The original front panel is dark blue with yellow/white legends (EMM); legend colours follow the original. |
| Display colours | all red | The original showed the program number in red and the delay time in yellow (EMM); red follows the brief. |

## C. Modern enhancements (blue legends, "EXT")

Tempo sync (11 divisions, list from PED), continuous delay time, GLIDE time changes, envelope sensitivity/release, soft loop saturation, LOW-cut slope switch, clean converter, true stereo, stereo width, wet only, output gain, preamp drive/tone/trim/auto-compensation, absolute parameter recall in programs (the original applied knob *offsets* to a recalled program), and the WRITE "TO" slot selector.

*v1.0.1 correction:* v1.0 listed the safety ceiling and the droop compensation here. They are engineering safeguards, not features, and now appear in section B.

## D. Not modelled

Hardware noise floor and hum, DRAM refresh artefacts, component tolerances and ageing, the DELAY MOD CV jack (use Live's modulators or MIDI mapping on Mod Intensity instead), footswitch jacks (MIDI-map HOLD / BYPASS / PROG ▲▼ instead), battery-backed memory behaviour.

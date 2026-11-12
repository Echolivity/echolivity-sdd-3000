# Musical evaluation — ECHOLIVITY SDD-3000 v1.0.2-rc4

**rc5 update:** P1, P3, P5 and P6 are now in the Manual. P2 became LOOP COMP with automatic CAL (the owner's Live test showed about 48 ms per pass, beyond the 30 ms first proposed). P4 is still waiting for listening.

**Device unchanged by this evaluation.** This round only measures and renders; it changes no DSP, parameter, preset or interface. Every proposal below needs the owner's approval and listening before anything is built.

## How it was done (and its limits)

- **Engine:** the C translation of the exact gen~ code in the device (`tools/gen2c.py`), at 48 kHz. Not Ableton Live and not the hardware.
- **Script:** `tests/musical_eval.py`. Re-run with `python3 tests/musical_eval.py`; raw numbers go to `docs/validation/MUSICAL_EVALUATION.json`.
- **Material:** synthesised and seeded (no third-party samples), at 75 BPM one-drop:
  1. isolated rimshot
  2. kick and snare
  3. dub bass line
  4. organ skank stabs
  5. a snare through a spring-style send and a rimshot through a plate-style send
  6. a dense mix of all of the above with hi-hats
  7. an aggressive FEEDBACK ride
  8. a 20 s evolving passage
- **Levels:** at the calibrated level (peaks at −17 dBFS = +4 dBm nominal), unless stated otherwise.
- **Limits:**
  - Nobody listened. Measurements show where the sound is likely to fall short; listening decides.
  - There is no A/B against a real SDD-3000. "Authentic" means "matches the service-manual / owner's-manual specification", not "matches a measured unit".
  - Synthesised drums are cleaner than real recordings.
  - The modulation measurement has a floor of about 7 cents from converter noise.

**Audio:** `audio_examples/musical_eval/*.flac` (lossless). Every file is normalised to the same peak, so you compare character, not loudness. Each material comes as `__dry`, `__conservative` (TIME 600 ms = dotted 1/8, FB 3, BAL 4) and `__dub_throw` (FB 6, LOW 250, HIGH 4k, BAL 6). Some also have `__dark_long` (FB 6.8, LOW 125, HIGH 2k). Files `7_*`–`10_*` belong to the findings below.

---

## Findings, ranked by musical impact

| # | Finding | Engineering | Authenticity | Musical impact | Proposal |
|---|---|---|---|---|---|
| F1 | **Gain staging:** at LEVEL 5, typical Live levels overload the converter heavily | correct; the meter is honest (overload starts exactly at the red +3) | authentic (the hardware needs gain staging by meter) | **High**: first-impression risk; hot sends give crunchy, flattened echoes | P1: documentation and quick-start only |
| F2 | **EXT loop timing:** each pass through the external track adds 1.3–10.7 ms | inherent to Live routing | n/a (modern feature) | **Medium-high**: repeats drift against the groove (up to 11 % of a 16th after 4 repeats at buffer 256) | P2: optional LOOP COMP trim, default 0 (bit-identical) |
| F3 | **Self-oscillation without LOW cut locks onto the kick's sub-bass (49 Hz)** | correct | authentic (flat response down to 20 Hz) | Medium: muddy rumble instead of a tone | P3: manual tip only |
| F4 | **SOFT ≈ HARD in sustained oscillation** (≤ 0.5 dB, same spectrum) | correct as designed | SOFT is a modern option | Medium: the switch may not be worth its panel space | P4: listening test first; no change |
| F5 | **Modulation at long delays is coarse at the bottom of INTENSITY** | correct | authentic (depth is proportional to delay time) | Low-medium: subtle tape-style wow needs very small knob moves | P5: manual tip (fine-adjust); taper change only after a Live check |
| F6 | **Stereo:** TRUE ST on a mono send stays mono; STEREO B loses 5.3 dB of wet in mono | correct | authentic (STEREO B = +MIX/−MIX) | Low: easy to misread | P6: manual note |

### Confirmed strengths

The device does these things right, so leave them alone:

- **Repeats degrade progressively and gracefully.**
  - **Rimshot at FLAT, FB 5:** each repeat loses about 5 % of its spectral centroid (1180 Hz at the source, 1094 Hz on the 1st repeat, 857 Hz on the 7th) and HF energy above 4 kHz falls from 4.8 % to 1.6 % of the total, consistent with the 17 kHz spec.
  - **Level:** −3.3 dB per repeat against the −2.92 dB law; the extra 0.4 dB is bandwidth loss on bright material.
  - **Transients:** crest factor holds (18.6 → 19.4 dB), so attacks stay intact at FLAT.
- **Filters in the loop shape the repeats strongly, as dub needs.**
  - **LOW 125 / HIGH 2k:** the centroid falls from 751 Hz to 497 Hz over 7 repeats, crest drops from 18.1 to 13.6 dB and attacks slow from 1.08 to 1.35 ms. Repeats get rounder and further away.
  - **LOW 250 / HIGH 4k:** the share of energy above 4 kHz falls from 1.4 % to under 0.1 % by the 4th repeat.
- **Converter character is authentic and subtle, as the hardware's 88 dB(A) spec implies.**
  - The 13-bit converter's own error is −75 dB below the signal at nominal and −66 dB at −35 dBFS input. It rises to about −55 dB in a fading tail, giving a faint grit only at the end of long tails.
  - At nominal, 13-bit and CLEAN measure identically to within 0.01 dB.
  - Idle output is exact digital silence.
- **Long passages stay controllable.** FB 8 SOFT with RND modulation while sweeping HIGH 8k → 4k → 2k → FLAT stays between −35 and −41 dBFS RMS for 16 s (peak −18 dBFS). It neither dies nor runs away (`8_long_evolving_*`).
- **FEEDBACK riding is predictable.**
  - Riding FB 4 → 10 reaches a converter-limited plateau in 3.9 s (peak −14 dBFS at BAL 6).
  - Back to 5, the level falls 30 dB in 7.2 s (12 repeats at 600 ms).
  - Nothing runs away. To kill the loop faster, ride FB lower or use BYPASS, which clears the memory.

### Rejected hypotheses (from my earlier review)

- **"HIGH stops at 2 kHz, so it isn't dark enough for classic dub throws."** Rejected. With LOW 125 / HIGH 2k the 6th repeat is centred around 500 Hz, and HF above 4 kHz is gone after 2 repeats. No darker setting is needed.
- **"Repeats should lose more high end, like the hardware."** Not supported. The measured per-repeat loss follows the documented 20 Hz–17 kHz response. There is no evidence that the real unit is darker than its spec, so I'm not proposing any change.
- **"The converter should add more grit."** Rejected under the governing principle: don't confuse distortion with character. The grit is at the level the spec implies.

---

## Details

### F1 — Gain staging (`gain_staging`, `desk_drive` in the JSON; files `9_desk_drive_snare_*`)

CLEAN converter, PRE off, error relative to a −40 dBFS linear reference:

| Input peak | Meter | kick+snare error | dub bass error | organ error |
|---|---|---|---|---|
| −20 dBFS | −3 | none | none | none |
| −17 dBFS | 0 | none | none | none |
| −14 dBFS | **+3 (red)** | −51 dB | −56 dB | −57 dB |
| −11 dBFS | +6 | −28 dB | −18 dB | −22 dB |
| −8 dBFS | +9 | −18 dB | −10 dB | −13 dB |
| −5 dBFS | +12 | −12 dB | −6 dB | −8 dB |
| 0 dBFS | +17 | −7 dB | −3 dB | −4 dB |

Snare echoes with the default converter: crest factor 9.6 dB at −17 dBFS peaks, 7.4 dB at −11, 3.1 dB at −5 and 1.5 dB at 0 dBFS (source 9.85 dB). The echo is also 1.8 dB quieter at −5 and 5.3 dB quieter at 0 dBFS.

**Reading it:** the converter clips exactly where the meter turns red, as on the hardware. But a Live track peaking at −6 dBFS, which is normal, reads about +11 on the meter at the default ATT +4 / LEVEL 5, and the echoes are then heavily clipped. A dub engineer can use that crunch deliberately; a new user will think the device distorts.

**P1 (documentation only, no device change):**
- Add a quick-start step: "set LEVEL so the HEADROOM meter peaks at 0 with only occasional red". At typical Live levels that's LEVEL 2–3, which is −6 to −8 dB.
- Explain that overdriving the converter is a sound, not a fault.

I don't propose changing the default calibration: that would change existing Sets, presets and the authentic +4 dBm reference.

### F2 — EXT loop timing (`ext_loop_timing`; files `10_*`)

| Live buffer @ 48 kHz | extra per pass | drift after 4 repeats | % of a 16th at 75 BPM |
|---|---|---|---|
| 64 | 1.3 ms | 5.3 ms | 2.7 % |
| 128 | 2.7 ms | 10.7 ms | 5.3 % |
| 256 | 5.3 ms | 21.3 ms | 10.7 % |
| 512 | 10.7 ms | 42.7 ms | 21.3 % |

The table assumes Live adds exactly one buffer per pass. That is the minimum; any latency from the devices on the loop track adds to it. **To be confirmed in Live (L-5c).**

**P2 (new optional control, needs approval):** LOOP COMP, 0–30 ms.
- **In EXT:** the internal write-to-read delay is shortened by this amount, so each external pass lands on time.
- **Default 0:** output is bit-identical to rc4.
- **In BOTH:** not applied, because it would make the internal repeats early.
- **Alternative:** measure the round trip automatically by correlating the send with the return. That's more complex and less predictable, so I don't recommend it as the first step.

### F3 — Self-oscillation tone (`self_oscillation_ride`; files `7_ride_fb_4-10-5_*`)

| Ride FB 4 → 10 → 5 (TIME 600 ms, BAL 6) | plateau RMS / peak | dominant | HF > 3 kHz | build-up | −30 dB after FB → 5 |
|---|---|---|---|---|---|
| HARD, FLAT | −21.6 / −14.0 dBFS | **49 Hz** | 0.72 % | 3.9 s | 7.2 s |
| SOFT, FLAT | −22.2 / −14.5 dBFS | 49 Hz | 0.68 % | 3.9 s | 7.2 s |
| HARD, LOW 500 / HIGH 2k | −48.5 / −29.0 dBFS | 190 Hz | 2.6 % | 2.3 s | 3.6 s |
| SOFT, LOW 500 / HIGH 2k | −48.5 / −29.3 dBFS | 190 Hz | 2.6 % | 2.3 s | 3.6 s |

- **At FLAT the oscillation builds on the kick's fundamental:** sub-bass rumble rather than a tone.
- **With LOW 500 / HIGH 2k it barely grows within 4 s at 600 ms.** The filter loss almost cancels the maximum loop gain of 10/7. That matches the service manual, which specifies oscillation at FB 10 with those filters at **50 ms**, where the loop passes much more often per second.

**P3:** add manual tips:
- For a controllable dub "scream", use LOW 250–500 with HIGH 8k or FLAT and a short-to-medium TIME.
- For long throws, ride FB to 8–9 rather than 10.

### F4 — SOFT vs HARD

In the table above the two differ by ≤ 0.5 dB and ≤ 0.05 % of HF energy. The soft curve only engages right at the converter's full scale, and the de-emphasis after the converter removes most of the extra harmonics. The difference may be audible on onsets, but the measurements say it is small.

**P4:** listen to `7_ride_fb_4-10-5_hard` against `7_ride_fb_4-10-5_soft`, and to `6_dense_mix__extreme_soft_fb9`.
- **If you can't hear a useful difference:** consider adding a distinctly voiced third mode later, and keep SOFT bit-identical for existing Sets.
- **Until then:** no change.

### F5 — Modulation movement (`modulation`)

Peak pitch deviation of the repeats (1 kHz tone, TRI, FB 0). The ~7-cent measurement floor dominates the 40 ms rows.

| TIME | FREQ (rate) | INTENS 0.5 | 1 | 2 | 5 |
|---|---|---|---|---|---|
| 380 ms | 2 (0.27 Hz) | 23 c | 39 c | 70 c | 152 c |
| 380 ms | 3 (0.45 Hz) | 34 c | 62 c | 113 c | 245 c |
| 40 ms | 2 (0.27 Hz) | ≤ 7 c | ≤ 8 c | 10 c | 18 c |
| 40 ms | 3 (0.45 Hz) | ≤ 7 c | 10 c | 14 c | 28 c |

- Pitch movement scales with delay time × depth × rate, as on the clock-modulated hardware.
- At dub echo times, subtle tape-style wow (≤ 10 cents) sits in the first ~0.2 of INTENSITY's travel.

**P5:**
- **Manual tip:** set INTENSITY with Live's fine adjustment, or MIDI-map it with a narrow range. At long TIMEs, keep FREQ at 1–2.
- **A knob-taper change would make the low end finer.** Before considering it, it needs a Live check that saved Sets and automation keep their values.

### F6 — Stereo (`stereo`; organ skank, FB 4)

| OUT MODE | L/R correlation | side vs mid | mono-sum change |
|---|---|---|---|
| MONO | 1.00 | — | 0 dB |
| STEREO A (DIRECT / +MIX) | 0.56 | −5.0 dB | −1.2 dB |
| STEREO B (+MIX / −MIX) | −0.41 | +3.8 dB | **−5.3 dB** |
| TRUE ST, mono source | 1.00 | — | 0 dB |
| TRUE ST, WIDTH 200 | 1.00 | — | 0 dB |

**P6:** add a manual note:
- A mono aux send into TRUE ST stays mono, and WIDTH can't widen identical channels. Use STEREO A or B for width from a mono send.
- STEREO B is the widest, but its wet signal partly cancels in mono.

---

## What I recommend next

1. **Apply P1, P3, P5 and P6 now.** They are documentation only, carry zero risk and need no device change.
2. **Listen to the `7_*` files** to settle F4.
3. **Approve or decline P2** (LOOP COMP) after the Live test L-5c confirms how much latency the external loop really adds.
4. **Keep everything else as it is.** The measurements support the current sound.

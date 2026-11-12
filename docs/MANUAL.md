# ECHOLIVITY SDD-3000 — User Manual

*A Max for Live digital delay modelled on the 1982 Korg SDD-3000 rack. Independent homage; not a Korg product.*

**White/yellow legends = original hardware functions. Blue legends ("EXT") = modern additions.** If you leave every blue control at its default, the device behaves like the original.

---

## Quick start: set the input level first (v1.0.2-rc5)

The converter overloads exactly where the HEADROOM meter turns red (+3). At the default ATT +4 / LEVEL 5, the meter reads 0 for peaks at −17 dBFS, the calibrated studio level. A typical Live track peaking around −6 dBFS reads about +11, and the echoes are then heavily clipped.

1. Play your source at its normal level.
2. Turn **LEVEL** down until the HEADROOM meter peaks around **0**, with the red **+3** only occasionally. For typical Live levels that's LEVEL **2–3**.
3. Then set FEEDBACK. The meter also shows the feedback, so recheck it at high FEEDBACK.

Overdriving the converter is a sound, not a fault: the crunch is authentic. Use it on purpose.

## Signal flow

```
IN ─► ATT (-30/-10/+4) ─► LEVEL ─► PREAMP (op-amp stage, tone, drive) ─┬─────────────► DIRECT
                                                                       │
                                     ┌──── regeneration (FEEDBACK, INV) ◄─────────┐
                                     ▼                                             │
                                  [ + ] ─► pre-emphasis ─► 13-bit A/D ─► 64K-word memory (64 kHz clock, LFO-modulated)
                                                                                   │
                                     D/A ─► de-emphasis ─► LOW cut ─► HIGH cut ─► EFFECT
DIRECT + EFFECT ─► BALANCE / output INV ─► MONO, STEREO A, STEREO B or TRUE STEREO ─► OUT ATT ─► OUT
```

## A. INPUT

| Control | Function |
|---|---|
| **ATT −30 / −10 / +4** | Input range. **+4** is clean for normal DAW levels: −17 dBFS in Live = nominal +4 dBm, and 0 dBFS is the clip point. **−10** adds 14 dB: hot sources crunch, as on the original. **−30** adds the Hi-Z amplifier (+34 dB) for heavy saturation. |
| **LEVEL** | Gain into the summing amp. 5 = nominal, 10 = +12 dB. |
| **HEADROOM** | Converter level of input **plus feedback**. Aim for peaks around 0, with the red +3 LED flashing only occasionally. |
| **PRE** | Turns the preamp character stage (op-amp clipping, tone, drive, output-stage clip) on or off. Off = clean linear gain. |
| DRIVE / TONE / TRIM | Preamp character (approximation). DRIVE pushes the op-amp stage. TONE tilts ±6 dB around 800 Hz. TRIM is output level. |
| COMP *(EXT)* | Auto level compensation for DRIVE. |

**Preamp only:** press **BYPASS**. The direct signal still passes through the preamp (the classic "used as a preamp" trick).

## B. DELAY

| Control | Function |
|---|---|
| **Display** | Program number (left; a dot = edited) and delay time in ms. In SYNC mode it shows the resulting ms. |
| **TIME** | 0–1023 ms. Hold Shift for fine adjustment. |
| 1ms / CONT *(EXT)* | Authentic 1 ms steps, or continuous. |
| XFADE / GLIDE *(EXT)* | How time changes sound. XFADE: a click-free 25 ms crossfade to the new time. GLIDE: tape-style pitch bend. |
| SYNC + DIV *(EXT)* | Lock to Live's tempo. Straight: 1/32, 1/16, 1/8, 1/4, 1/2, 1/1. Triplets (**T**): 1/8T, 1/4T, 1/2T, and at the end of the menu 1/16T and 1/32T (rc5). Dotted (**D**): 1/8D, 1/4D. Anything longer than 1023 ms is clamped. Up to rc4 the triplets were labelled 1/12, 1/6, 1/3 and the dotted values 3/16, 3/8; the values haven't changed, so old Sets and programs recall the same division. |

## C. MODULATION

The original sweeps the **memory clock**, so the whole delay line changes speed. That's where its flange and pitch-shift character comes from.

| Control | Function |
|---|---|
| **WAVE** | **TRI**: chorus, flange, vibrato; sharp peaks, rounded troughs. **SQR**: jumps between two clock speeds for pitch-shifted echoes and trills (up to an octave at INTENSITY 10). **RND**: smoothed random level, new value once per cycle; keep INTENSITY low. **ENV**: follows the input; louder means shorter delay (Doppler, "parachute" effects). |
| **INTENSITY** | 0–10. At 10, the delay swings from the set time down to half of it (2:1). It never goes longer than the display. |
| **FREQUENCY** | 0 = 0.1 Hz (10 s), 10 = 15 Hz. The LED follows the LFO. Also sets the RND rate. |
| ENV SENS / ENV REL *(EXT)* | Envelope sensitivity and release. The default 1440 ms matches the original's ≈2 s decay. |

## D. REGENERATION

| Control | Function |
|---|---|
| **FEEDBACK** | 0–10. Each repeat changes level by FEEDBACK/7. **Above about 7 the loop self-oscillates, as on the original.** The converter clip bounds it, so it never runs away. |
| **INV** | Inverts the feedback phase: hollow flange, different comb pitch. |
| **HOLD** | Freezes the last ~1 s and loops it forever with no loss. New input is **not** recorded, so you can play over it. Filters, INV and modulation still act on the loop. Press again to release: the loop keeps playing until the first new echo arrives (one delay time later), then crossfades into it in 10 ms. At TIME settings above ~944 ms the loop fades out slightly before the first new echo (gap of up to ~80 ms), because the 64K-word memory cannot hold both. Pressing HOLD again while the loop is still audible keeps it. |
| **LOW** | FLAT / 125 / 250 / 500 Hz cut, −3 dB/oct (service-manual spec). |
| **HIGH** | FLAT / 8k / 4k / 2k Hz cut, −6 dB/oct. Both filters are inside the loop, so every repeat gets darker or thinner. |
| HARD / SOFT *(EXT)* | Loop limiting. HARD = converter clip (authentic). SOFT = smoother saturation for dub swells. |
| 3dB / 6dB *(EXT)* | LOW cut slope. Use 6 dB if you prefer a conventional slope. |
| FB ROUTE *(EXT, rc4)* | **INT**: normal internal loop. **EXT**: the loop runs through another Live track (see below) and the internal loop is off. **BOTH**: internal loop plus the external one. |
| RETURN *(EXT, rc4)* | 0–10. Level of the external loop coming back, same law as FEEDBACK (each pass × RETURN/7). Default 5. Ignored in INT. Accepts Live's LFO in Mod mode. |

### External regeneration loop (v1.0.2-rc4)

Like patching the echo's feedback through a mixing desk: the repeats leave the device, pass through whatever is on another track (reverb, EQ, a filter, a spring, distortion…) and come back into the delay memory, so every repeat goes through those effects again.

The device has an extra stereo **output 3/4 (send)** and **input 3/4 (return)**:
- **Send (out 3/4)** always carries the regeneration signal, after LOW/HIGH, at unity gain, in every FB ROUTE mode.
- **Return (in 3/4)** is used only in EXT and BOTH, scaled by RETURN.

Setting it up in Live:
1. Put ECHOLIVITY on a track (say track A). Set **FB ROUTE** to **EXT** and **RETURN** to about 5.
2. Create an audio track for the loop (track B) and load the effects you want on it.
3. On track B, set **Audio From** to track A and, in the chooser below it, choose ECHOLIVITY's **3/4** output. Set **Monitor** to **In**.
4. Set track B's **Audio To** to track A and, below it, choose ECHOLIVITY's **3/4** input.
5. Play. RETURN, track B's fader and the effects on track B together set how long the repeats last.

Notes:
- Each pass through track B adds Live's routing latency: at least one audio buffer, plus any latency of the effects on track B. Without compensation the repeats arrive late, by 46 ms per repeat at a 2048-sample buffer. Use **CAL** (below).
- RETURN above 7 (or gain on track B) builds up until the converter limits it, like FEEDBACK above 7.
- Track B normally isn't heard directly, only through the echoes. Turn its Audio To back to Main to hear the send on its own.
- HOLD and BYPASS work as usual: while HOLD is on, the return isn't recorded.
- Confirmed in Live 12 Suite on Windows by the owner: Live offers ECHOLIVITY's 3/4 in both choosers and runs the loop.

**LOOP COMP and CAL (v1.0.2-rc5):** these put the external repeats back on the beat.
1. Set up the loop as above with FB ROUTE on **EXT**.
2. Press **CAL**. The loop pauses for about half a second while ECHOLIVITY sends one click through track B, times its return and writes the result into **COMP ms**.
3. That's it. In EXT the delay is now shortened by COMP ms, so each repeat lands exactly on TIME / the synced division.

- Press CAL again after changing the buffer size or the effects on track B. You can also type COMP ms by hand (0–250 ms).
- **If COMP ms doesn't change after CAL,** the click didn't come back clearly. Check the routing, raise track B's fader to 0 dB, or bypass a 100 %-wet reverb on track B for the moment of the CAL press.
- **COMP ms is applied in EXT only.** In BOTH it would make the internal repeats early, so it's ignored. In INT the external loop isn't used.
- The TIME display keeps showing TIME, not the compensated value.

## E. EFFECT / OUTPUT

| Control | Function |
|---|---|
| **BALANCE** | 0 = direct only, 5 = 1:1, 10 = effect only. This is the dry/wet control. |
| **INV** (output) | Inverts the effect in the mix: sum ↔ difference. Not stored in programs, as on the original. |
| **BYPASS** | All outputs direct. The delay input is muted, so an existing loop is cleared. |
| **ATT −20 / −10 / +4** | Output level. +4 with input +4 is unity. |
| **OUT MODE** | **MONO**: the front VARIABLE output on both sides. **STEREO A**: DIRECT left, +MIX right (mono-compatible; the original's recording setup). **STEREO B**: +MIX left, −MIX right (wide; the effect cancels in mono). **TRUE ST** *(EXT)*: independent L/R delays. |
| WIDTH, GAIN, WET ONLY *(EXT)* | Stereo width, output gain (±), and dry removed from all outputs (for return tracks). |
| 13-BIT / CLEAN *(EXT)* | Converter character. CLEAN removes quantisation; everything else stays the same. |

**Output protection is soft saturation, not a 0 dBFS limiter.** With PRE on and the default output settings, the modelled output amplifier saturates softly toward 0 dBFS. With PRE off or OUTPUT GAIN above 0 dB, the output can exceed 0 dBFS. A safety curve (transparent to +6 dBFS) stops it at +12.04 dBFS at most. Details: `docs/OUTPUT_PROTECTION.md`.

## F. PROGRAM MEMORY

- **M** is manual (the live panel). **1–9** are stored programs. ▲/▼ step through them and can be MIDI-mapped to footswitches.
- A program stores TIME, FEEDBACK, INV, LOW, HIGH, WAVE, INTENSITY, FREQUENCY and BALANCE (as on the original), plus 1ms/CONT, SYNC and DIV. Input, output, HOLD and output INV are not stored.
- Moving a control after recalling a program lights the **dot** next to the program digit. The edit lasts until you change program.
- **WRITE** stores the current panel into slot **TO**. TO follows the selected program, so WRITE on a recalled program overwrites it.
- The M panel is remembered when you leave it and restored when you return.
- All programs are saved with your Live Set and in Live device presets (.adv). To restore the factory bank, load a fresh instance of the device.

### Factory programs

| # | Name | Highlights |
|---|---|---|
| 1 | Classic Echo | 380 ms, LOW 125 / HIGH 4k so repeats darken naturally |
| 2 | Short Slap | 123 ms, owner's-manual slapback setting |
| 3 | Dub Regeneration | dotted 1/8 sync, FB 6.6, LOW 250 / HIGH 2k. Push FEEDBACK past 7 for swells |
| 4 | Metallic Flange | 4 ms, INV, owner's-manual flanging setting |
| 5 | Wide Doubling | 33 ms, owner's-manual doubling setting. Use OUT MODE STEREO A |
| 6 | Vibrato | effect only, 5 ms, TRI ≈4.5 Hz |
| 7 | Random Drift | smoothed RND, gentle tape-like wander |
| 8 | Infinite Hold | 1023 ms, flat. Play a phrase, press HOLD, solo over it |
| 9 | Rhythmic Modulation | SQUARE pitch-stepped echoes, dotted 1/8 sync |

## Automation and MIDI

Every panel control is a Live parameter. It can be automated, MIDI-mapped (Ctrl/Cmd-M), key-mapped and macro-mapped. Push / Configure banks: **Delay**, **Character**, **Modern**. The hidden program-memory slots are "stored only", so they're saved but don't clutter the automation lists.

### LFO and modulators (v1.0.2-rc3)

The 13 continuous knobs accept Live's LFO, Shaper and other modulators in **Mod** mode (the cyan button): TIME, FEEDBACK, BALANCE, INPUT LEVEL, OUTPUT GAIN, INTENSITY, FREQUENCY, ENV SENS, ENV RELEASE, WIDTH, and Preamp DRIVE, TONE, TRIM. They use *Additive* modulation: the modulator swings the knob around wherever you set it, without moving the knob itself, so automation, presets and **WRITE** keep the knob's own setting.

Stepped controls (switches, tabs, menus such as LOW/HIGH CUT, WAVEFORM, DIVISION, HOLD, PROGRAM) can't be modulated in Mod mode; Live never allows that for stepped parameters. Map them with the modulator's Mod button **off**: they then jump between steps.

Tips:
- **TIME** follows the TIME CHANGE switch. In *glide* an LFO gives tape-style pitch wobble, but the delay time follows at a limited speed (like the hardware's clock), so it **lags a fast LFO**. In *crossfade* it gives choppy, stepped re-timing. For a classic chorus/flange, use the device's own MODULATION section instead; it works on the memory clock, as the hardware did.
- **What you see:** in Mod mode the knob and its number stay where you set them (e.g. "456 ms"); only the ring shows the LFO. That's how Live displays Additive modulation.
- **INTENSITY at long delay times:** pitch movement grows with delay time. At TIME 380 ms, INTENSITY 0.5 already gives about ±23 cents, so subtle tape-style wow sits in the first ~0.2 of the knob. Use Live's fine adjustment (hold Shift while dragging) or MIDI-map it with a narrow range.
- **FEEDBACK** with an LFO gives swelling and fading dub tails. Keep the depth moderate near 10.
- **BALANCE** with a slow LFO fades the echoes in and out.

## Robustness (v1.0.2)

- If an upstream device sends invalid audio (NaN or infinite samples), ECHOLIVITY treats those samples as silence/overload and keeps working; no reload is needed. Normal audio is processed exactly as before.
- Known limitations and items still to be verified in Live: `docs/OUTSTANDING_ISSUES.md`.

## Tips for a live dub session

- Put the device on a return track, turn WET ONLY on, and use OUT MODE STEREO A or B.
- MIDI-map HOLD, BYPASS, FEEDBACK and HIGH to a controller. Throw a snare into the send, push FEEDBACK to 7–8, sweep HIGH, then BYPASS to clear the loop.
- SOFT loop saturation rounds off the onset of self-oscillation; in sustained oscillation it measures very close to HARD (the authentic converter grit).
- **Controlled "scream":** with LOW cut FLAT, self-oscillation builds on the kick's sub-bass (around 50 Hz) and turns to rumble. Use LOW 250–500 with HIGH 8k or FLAT and a short-to-medium TIME. For long throws, ride FEEDBACK to 8–9 rather than 10.
- **Stereo from a mono send:** TRUE ST keeps a mono send mono, and WIDTH can't widen identical channels. Use STEREO A or B for width. STEREO B is the widest, but its echoes partly cancel when the mix is summed to mono (about −5 dB).

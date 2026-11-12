# Optional physical measurement through an audio interface

This workflow measures ECHOLIVITY **as it runs inside Ableton Live**, through a real audio interface. The interface's own response, level and latency are measured first and divided out. It extends the automated suite (which measures the C build of the gen~ code) to the real host.

**What this measures:** the software, in Live, through your converters.
**What it does not do:** establish equivalence to an original 1982 SDD-3000. Only running the same stimulus through an original unit could do that.

Tool: `tools/loopback_measure.py`. Its analysis code is checked on every run of `tests/hwref/hw_validation.py` against a simulated interface (latency, band-limiting, gain, noise): latency is recovered exactly and the response within 0.2 dB.

## 1. Prepare

1. **Equipment:** one interface with a line output and a line input. Use a short balanced cable, or the interface's internal loopback if it has one.
2. **Live settings:**
   - Sample rate 48 kHz (repeat at 44.1 and 96 kHz if you want the rate dependence).
   - Note the buffer size.
   - Disable the warp and fades on the playback clip.
3. **Interface settings:**
   - Switch off any DSP mixer effects, phantom power and input pads you don't need.
   - Set the input gain so the stimulus's −10 dBFS tone peaks around −12 dBFS on the input.
   - **Write the setting down, and don't touch it again until both captures are done.**
4. **Generate the stimulus** (48 kHz, 32-bit, 21 s). It contains a sync click, 1 kHz tones at −20 and −10 dBFS, a −30 dBFS log sweep from 10 Hz to 22 kHz, and silence.

   ```
   python3 tools/loopback_measure.py generate --rate 48000 --out stim.wav
   ```

## 2. Capture

1. **Loopback (interface only):**
   - Track A plays `stim.wav`, routed to output 1.
   - Track B records input 1, with Monitor Off.
   - Bounce or export track B as `loopback.wav`.
2. **Device:**
   - Put ECHOLIVITY on track A with the settings under test. For the reference response use TIME 0, FEEDBACK 0, BALANCE 10, CONVERTER CLEAN, PRE off, OUT MODE MONO.
   - Record again and save as `device.wav`.
3. **Record the conditions:** Live version, interface model, sample rate, buffer size, input gain, device settings, date.

**Avoid clipping:** the analysis warns if any capture peaks above −1 dBFS. The device's own converter overloads about 5 dB above nominal, so the −10 dBFS tone is a deliberate high-level test. The sweep runs at −30 dBFS so the response measurement stays below that point.

## 3. Analyze

```
python3 tools/loopback_measure.py analyze --stimulus stim.wav --loopback loopback.wav \
    --device device.wav --conditions "Live 12.x, <interface>, 48 kHz, buffer 256, settings ..." \
    --out results/echolivity_48k
```

The tool writes `results/echolivity_48k.json` and `.md`, containing:

| Output | What it is |
|---|---|
| Latency | Loopback and device latency (sync-click cross-correlation), and the device's extra latency |
| Frequency response | The device capture divided by the loopback capture (log-sweep deconvolution), so the interface's response and level cancel |
| 1 kHz tones | Level, THD (harmonics 2–10) and total distortion + noise at −20 and −10 dBFS, for both captures. Compare the device figures with the loopback figures: the interface's own distortion and noise are included in both |
| Noise floor | From the silent section, for both captures |

Commit the JSON/MD files under `docs/validation/measurements/` with the conditions filled in, if you want them in the release evidence. The automated suite never edits them.

## 4. Optional comparison with commercial emulations

A commercial SDD-3000 emulation can serve as a **secondary** reference. It's never ground truth, and a similar measurement or a similar sound doesn't prove hardware equivalence.

1. In Live, put the plug-in on a track playing `stim.wav`. Use settings that correspond to the ECHOLIVITY settings (document both), then **Export Audio** (offline render) as `plugin.wav`.
2. Render ECHOLIVITY the same way as `echolivity.wav`.
3. Analyze each one, with the stimulus itself as the "loopback": a digital render has no interface to remove.

   ```
   python3 tools/loopback_measure.py analyze --stimulus stim.wav --loopback stim.wav --device plugin.wav --out cmp/plugin
   python3 tools/loopback_measure.py analyze --stimulus stim.wav --loopback stim.wav --device echolivity.wav --out cmp/echolivity
   ```

4. Document the differences numerically, alongside the 1982 documentation figures (`HARDWARE_REFERENCE.md` §3).

Rules:
- No proprietary DSP is inspected, decompiled or copied.
- Results are labelled "secondary reference".
- Disagreements are resolved in favour of the original documentation, not the plug-in.

## 5. Status

This workflow hasn't been run on real equipment yet. No results from it exist in this repository.

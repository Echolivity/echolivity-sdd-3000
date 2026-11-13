# HW-1 Candidate D — Native Max 9 / Live 12 Validation

**Status: NOT PERFORMED.** No Max 9 or Live 12 run of candidate D exists. This document contains the test build and the protocol; results are to be filled in from an actual session. Nothing here may be read as native validation.

## Test build

- Device: `experiments/hw1/candidate/ECHOLIVITY SDD-3000 HW1-D TEST.amxd` (sha256 `5be387cb3fbb346be7d5ea63fbbc463cf78f4ecc7f5d9863b68f5a9fff6d3649`).
  - Built by `experiments/hw1/make_test_device.py` from the unmodified production generator (`tools/build_amxd.py`).
  - Only the gen~ code is swapped: `experiments/hw1/candidate/echolivity_core_d.genexpr`.
  - The panel legend reads **ECHOLIVITY HW1-D TEST**.
- Statically identical to the release (`experiments/hw1/results/test_device_compat.json`):
  - 162 of 162 parameters;
  - Push banks;
  - 120 of 120 program values.
- Keep the release device (`dist/ECHOLIVITY SDD-3000.amxd`) on a second track for A/B.

## Protocol

| # | Check | How | Pass |
|---|---|---|---|
| N1 | gen~ compiles | Drop the device in Live 12. Open it in Max 9 and open the `gen~` patcher. | No red box. No gen~ errors or warnings in the Max console. The console is otherwise as it is for the release (the known `parameter '<unknown>' not found` lines are acceptable if the release shows them too). |
| N2 | Audio runs, no dropouts | Play a dense loop at 48 kHz, buffer 128, for 5 min with the program changed every 30 s. | No dropouts and no clicks beyond the release's. |
| N3 | CPU | Live's CPU meter, and Max's CPU, for 1 and 8 instances at 44.1 / 48 / 96 kHz, buffers 64 / 128 / 512. Same for the release device. | Note both. Target: D ≤ 1.5× the release. |
| N4 | Sample-rate switching | Change Live's rate 44.1 → 48 → 96 → 192 → 44.1 kHz while playing, with FB 6 and TIME 380. | No silence lock-up, no burst, no NaN. Repeats continue at the same TIME. |
| N5 | HW-1 audible check | 17 kHz sine at −20 dBFS into each device at 48 kHz, BALANCE 10, TIME 20 and TIME 0. Spectrum on the output (Live's Spectrum device). | The release shows lines at 1 kHz and 15 kHz. D shows none above the floor (about −80 dB re tone or lower). |
| N6 | TIME 0 | TIME 0, BALANCE 5, broadband material. Then step TIME 0 → 1 → 0 ms. | Same timbre as the release apart from the spurs. No comb change. Switching is click-free. |
| N7 | Presets | Recall all 9 factory programs, and a user preset saved in the release. | Values identical to the release. |
| N8 | State | Save a Set with D at non-default settings, close, reopen. Also freeze/flatten a track. | All settings restored. Frozen audio matches live playback. |
| N9 | Delay timing | Click track, TIME 100 / 380 / 1023, FEEDBACK 0. Measure echo positions in an audio recording. | Echo at TIME within 1 sample of the release's position (D is about 17 µs earlier at 48 kHz). |
| N10 | HOLD | HOLD at TIME 380 with FB 3; release; re-engage. | Click-free, as with the release. |
| N11 | Listening | P1–P9 A/B against the release on the owner's material, and `experiments/hw1/audio_d/*.flac`. | The owner accepts the character, especially P4, P6 and P8 above 10 kHz. |

## Results

| # | Result | Notes |
|---|---|---|
| N1–N11 | *not run* | |

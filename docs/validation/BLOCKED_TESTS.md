# Blocked and unverified tests — v1.0.2-rc5

**BLOCKED** = requires Ableton Live 12 / Max, which was unavailable, so the test was not executed. **UNVERIFIED** = an assumption about the Max/Live runtime that no executed test covers.

## BLOCKED (not executed)

| # | Test (checklist ID) |
|---|---|
| 1 | ~~Device loads in Live 12~~ **done by the owner: PASS**; device initialisation (L-1) |
| 2 | ~~gen~ compiles; audio passes, no clicks~~ **done by the owner (rc4): PASS**. Console: UI-2 fixed in rc5, reconfirm |
| 3 | Audio input/output and stereo routing in all OUT MODEs (L-2) |
| 4 | Compiled DSP in Live matches the reference renders (L-3) |
| 5 | Parameter automation, recording and playback (L-4) |
| 6 | MIDI mapping (L-5) |
| 6b | ~~LFO Mod mapping accepted~~ **done by the owner: PASS** (TIME); audible following and the other knobs not separately confirmed (L-5b) |
| 6c | ~~EXT loop: choosers, circular routing~~ **done by the owner: PASS** (L-5c) |
| 6d | **rc5: CAL measures the loop and LOOP COMP puts repeats on the beat (L-5d)** |
| 6e | **rc5: triplet divisions 1/16T, 1/32T; old Sets recall the same division (L-6b)** |
| 6f | **rc5: UI-2 fixed: no `parameter '<unknown>' not found` in the Console** |
| 7 | Tempo sync and tempo automation (L-6) |
| 8 | ~~Program switching, WRITE/recall~~ **done by the owner: PASS**; edit dot and `.adv` save/load not yet run (L-7) |
| 9 | **D-1 fix confirmation: `.adv` hot-load in M restores the saved values** (L-7a) |
| 10 | **D-2 reproduction: re-selecting the active program** (L-7b) |
| 11 | Set save/reopen, state persistence, no ramps at load (L-8) |
| 12 | ~~HOLD activation, release, rapid re-engagement~~ **done by the owner: PASS** (L-9) |
| 13 | BYPASS in Live (L-10) |
| 14 | Host sample-rate change in Live (L-11) |
| 15 | Invalid-input recovery in Live (gen~ `fixnan`) (L-12) |
| 16 | 8 instances without dropouts: **done by the owner: PASS** (44.1 kHz, one buffer size). Still open: CPU at 44.1/48/88.2/96 kHz × buffers 64–1024, 1 and 8 instances, during automation and HOLD + feedback; no dropouts (L-13) |
| 17 | Plugin-reported latency / PDC readout; dry-path null test (L-14) |
| 18 | Interface appearance in Live (L-15): UI-1 fixed and panel visible (owner); detailed look and LED/meter updates not yet checked |
| 19 | Backward compatibility: v1.0/v1.0.1 Sets and `.adv` presets load correctly into rc5 (L-7, L-8) |

## UNVERIFIED runtime assumptions

| Assumption | Where it matters |
|---|---|
| gen~ `fixnan` replaces NaN with 0 (no fast-math elimination) | invalid-input protection |
| gen~ Param `min`/`max` clamp behaves like the C harness | out-of-range messages |
| `live.text` in button mode outputs `1` or `bang` (both handled) | WRITE, PROG ▲/▼ |
| `live.tab` re-outputs when its selected cell is clicked | D-2 |
| `plugin~ 1 2 3 4` / `plugout~ 1 2 3 4` appear in Live as routable 3/4 pairs on an audio effect | EXT loop |
| Live allows track B ← device out 3/4 and track B → device in 3/4 at the same time (circular routing) | EXT loop |
| Live honours `parameter_order` during a preset load (Program first) | D-1 fix, second part |
| `parameter_modmode` 3 = Additive and is accepted by Live's Mod mapping | LFO Mod mapping |
| The 7-segment display and meters render and update as in `docs/ui_preview.png` | interface |
| Test tooling runs on Windows/macOS (Python + C compiler) | developer workflow only |

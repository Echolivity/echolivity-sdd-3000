# LFO pointers (rc8): native test record

- **Build:** 1.0.2-rc8 (merged from `feature/lfo-pointer`, based on rc7)
- **Device under test:** `ECHOLIVITY SDD-3000 (LFO pointer test 2).amxd` (geometry re-measured from the owner's screenshot of test build 1)
- **Tester:** owner, Ableton Live 12.4.6 (bundled Max 9), Windows, 2026-11-14
- **Test build 1:** pointers slightly too high and too large, 270° sweep vs Live's 300°. Measured and corrected in test build 2.

| # | Check | Pass criterion | Result |
|---|---|---|---|
| 1 | Load; take a screenshot of the whole panel with no LFO | Each blue pointer lies exactly on its knob's white needle (all 13 knobs) | **PASS** (build 2): all 13 hidden under the white needles, screenshot |
| 2 | Turn several knobs by hand, including TIME and ENV REL | The blue pointer stays on the white needle across the whole range | **PASS** |
| 3 | Live LFO, Mod on, mapped to BALANCE, slow rate, large amount | The blue pointer swings; the knob and its number stay; the mix follows | **PASS** |
| 4 | Same on TIME (glide) and FEEDBACK | Pointer swings within the knob's range and stops at the ends | **PASS** |
| 5 | Click and drag every knob, double-click to reset | Knobs respond exactly as before (pointers don't block clicks) | **PASS** (drag and double-click reset) |
| 6 | Program recall, Set save / reopen | Pointers follow the recalled values | **PASS** with the LFO removed. With the LFO still mapped, the pointers keep following it after recall, which is expected: recall doesn't remove a Live modulation mapping |

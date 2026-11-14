# REVERSE (rc7): native test plan

- **Build:** 1.0.2-rc7 (merged from `feature/reverse-regen`)
- **Device under test:** `dist/ECHOLIVITY SDD-3000.amxd` (the `(REVERSE test)` copy sent earlier is identical)
- **Tester / date / Live and Max version:** owner, 2026-11-14, Ableton Live 12.4.6 (bundled Max 9), Windows; device = `LFO pointer test 2` build (rc7 DSP + LFO pointers)
- **Results:** checks 3–13 PASS (owner-reported, 2026-11-14; checks 6–13 reported in one confirmation, no measurements noted). Checks 1 and 2 not run. Offline engine results are in `docs/TEST_RESULTS.json` (REVERSE tests); they are not a substitute for these checks.

Setup: one audio track, a short drum loop or plucked notes, TIME 400, FEEDBACK 5, BALANCE 6.

| # | Check | Pass criterion | Result |
|---|---|---|---|
| 1 | Load the test device; open it in Max and look at the Max Console | Loads, panel shows the REVERSE menu at OFF, no errors | |
| 2 | REVERSE OFF | Sounds exactly like rc6 | |
| 3 | REV | Every repeat is backwards (swelling attacks) | **PASS** |
| 4 | ALT, then ALT R, FEEDBACK 6 | ALT: 1st forwards, 2nd backwards, 3rd forwards. ALT R: the opposite | **PASS** (ALT at FEEDBACK 5; ALT R) |
| 5 | Switch OFF → REV → ALT → ALT R → OFF while repeats ring | No clicks or dropouts | **PASS**: no clicks |
| 6 | HOLD in REV, play over it, release | HOLD loop plays forwards; release is click-free | **PASS** |
| 7 | TIME 60 and TIME 1023 in REV | Short: grainy, no clicks. Long: slow reverse swells | **PASS** |
| 8 | FEEDBACK 10 in each mode | Builds up but stays bounded | **PASS** |
| 9 | FB ROUTE EXT through another track (SEND / RTN menus) in ALT | Repeats pass through the other track and still alternate | **PASS** |
| 10 | Automate Reverse in an automation lane; map it to a MIDI control | Follows; the parameter is named "Reverse" | **PASS** |
| 11 | Save the Set with REVERSE on ALT, reopen | REVERSE still on ALT | **PASS** |
| 12 | Program recall: WRITE to a slot with REV on, switch programs | REVERSE is not changed by program recall | **PASS** |
| 13 | CPU meter: OFF vs ALT R, 4 instances | Note both values; no dropouts | **PASS** (no dropouts reported; CPU values not recorded) |

# REVERSE (feature branch): native test plan

- **Branch:** `feature/reverse-regen` (not merged)
- **Device under test:** `ECHOLIVITY SDD-3000 (REVERSE test).amxd`, identical to `dist/ECHOLIVITY SDD-3000.amxd` on the branch
- **Tester / date / Live and Max version:** to be filled in
- **Results:** none yet. Offline engine results are in `docs/TEST_RESULTS.json` (REVERSE tests); they are not a substitute for these checks.

Setup: one audio track, a short drum loop or plucked notes, TIME 400, FEEDBACK 5, BALANCE 6.

| # | Check | Pass criterion | Result |
|---|---|---|---|
| 1 | Load the test device; open it in Max and look at the Max Console | Loads, panel shows the REVERSE menu at OFF, no errors | |
| 2 | REVERSE OFF | Sounds exactly like rc6 | |
| 3 | REV | Every repeat is backwards (swelling attacks) | |
| 4 | ALT, then ALT R, FEEDBACK 6 | ALT: 1st forwards, 2nd backwards, 3rd forwards. ALT R: the opposite | |
| 5 | Switch OFF → REV → ALT → ALT R → OFF while repeats ring | No clicks or dropouts | |
| 6 | HOLD in REV, play over it, release | HOLD loop plays forwards; release is click-free | |
| 7 | TIME 60 and TIME 1023 in REV | Short: grainy, no clicks. Long: slow reverse swells | |
| 8 | FEEDBACK 10 in each mode | Builds up but stays bounded | |
| 9 | FB ROUTE EXT through another track (SEND / RTN menus) in ALT | Repeats pass through the other track and still alternate | |
| 10 | Automate Reverse in an automation lane; map it to a MIDI control | Follows; the parameter is named "Reverse" | |
| 11 | Save the Set with REVERSE on ALT, reopen | REVERSE still on ALT | |
| 12 | Program recall: WRITE to a slot with REV on, switch programs | REVERSE is not changed by program recall | |
| 13 | CPU meter: OFF vs ALT R, 4 instances | Note both values; no dropouts | |

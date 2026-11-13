# rc6 SEND / RTN routing menus: native test record

- **Tester:** owner
- **Date:** 2026-11-13
- **Software:** Ableton Live 12.4.6 (bundled Max 9)
- **Device:** `ECHOLIVITY SDD-3000 (rc6 SEND-RTN test).amxd`, identical to `dist/ECHOLIVITY SDD-3000.amxd` at commit `c03aabb`

| # | Check | Result |
|---|---|---|
| 1 | Device loads; Max for Live console clean; menus show Live's state ("No Output" / "No Input") | PASS |
| 2 | Left SEND menu lists the destinations (Ext. Out, 3-Audio, 4-Audio, A-Reverb, B-Delay, No Output) | PASS (screenshot) |
| 2 | Left RTN menu lists the sources (Ext. In, Track A, Track B, 3-Audio, 4-Audio, A-Reverb, B-Delay, Main, No Input) | PASS (screenshot) |
| 3 | FB ROUTE EXT; SEND 3-Audio / Track In, RTN 3-Audio / Post FX; repeats pass through 3-Audio's effect and come back | PASS (screenshot of the channel menus) |
| 4 | Changing 3-Audio's Audio From in Live is reflected in the SEND menu | PASS |
| 5 | Save, close, reopen: SEND and RTN still on 3-Audio; the loop plays immediately | PASS |
| 6 | Rename, add and delete tracks: the menus update by themselves | PASS |
| 7 | FB ROUTE INT; factory programs: unchanged behaviour | PASS |

Notes:
- SEND lists only tracks that can receive audio. The host track is not offered.
- RTN also offers Main and the return tracks.
- No fallback storage is needed: Live saves the DeviceIO routing with the Set.

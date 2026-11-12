# Installation (Windows and macOS)

**Requirements:** Ableton Live 12 Suite, or Live 12 Standard with Max for Live. No other software, externals or paid dependencies. The device is a single self-contained file: the gen~ DSP is embedded, and the interface uses only native Max for Live objects.

## Install

1. Download `ECHOLIVITY SDD-3000.amxd` (from `dist/`, or unzip a release package first).
2. Copy it into your User Library, for example:
   - Windows: `C:\Users\<you>\Documents\Ableton\User Library\Presets\Audio Effects\Max Audio Effect\`
   - macOS: `~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/`
3. In Live's browser, open **User Library → Presets → Audio Effects → Max Audio Effect** and drag **ECHOLIVITY SDD-3000** onto an audio track or return track.

You can also drag the .amxd straight from Explorer/Finder onto a track.

## First run

- Expected: the display shows `0  380` and the TIME dial reads 380 ms.
- Replacing an earlier version: save your Set first. No parameter was removed or renamed. 1.0.2-rc4/rc5 added four parameters (FB Route, Ext Return, Loop Comp, Loop Cal) and two sync divisions (1/16T, 1/32T, appended so existing division settings recall unchanged); see `docs/validation/PRESET_COMPATIBILITY_REPORT.md`. Reopening older Sets in Live hasn't been validated yet.
- Play audio. The HEADROOM LEDs should move and you should hear echoes.
- If the device loads but stays silent, open it in Max (the wrench icon) and check the Max Console for gen~ errors. Please report the message. Loading in Live 12 Suite on Windows has been confirmed by the owner (rc4); macOS and other Live versions are untested. See `docs/validation/LIVE_INTEGRATION_REPORT.md`.

## Updating

Live caches loaded devices. After replacing the .amxd, delete the device from the track and drag it in again, or reopen the Set.

## Verify the download (optional)

Compare the device's SHA-256 with `SHA256SUMS.txt`:
- Windows (PowerShell): `Get-FileHash ".\dist\ECHOLIVITY SDD-3000.amxd" -Algorithm SHA256`
- macOS: `shasum -a 256 "dist/ECHOLIVITY SDD-3000.amxd"`

## Sources (optional)

`src/gen/echolivity_core.genexpr` is the exact code inside the gen~ box. Rebuild and test commands are in `README.md`. The test suite needs Python 3, numpy, scipy and a C compiler; it creates its own `build/` folder.

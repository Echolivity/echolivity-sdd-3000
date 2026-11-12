# ECHOLIVITY SDD-3000 — v1.0.2-rc5 (release candidate)

**Release candidate — CONDITIONAL PASS, not production-ready.** rc5 adds triplet sync divisions and LOOP COMP / CAL for the external loop, fixes the Max Console flood (UI-2), and records the owner's first Live 12 results. rc4 fixed a blank panel in Live 12 (UI-1) and added an **external regeneration loop** (FB ROUTE / RETURN, device in/out 3-4). rc3 added LFO "Mod" mapping on the 13 continuous knobs and the D-1 preset hot-load fix; DSP, sound, presets and interface are unchanged. Ableton Live validation is still outstanding. Start with `docs/validation/RELEASE_DECISION.md`.

A Max for Live digital delay for Ableton Live 12, modelled on the 1982 Korg SDD-3000 rack. *Independent homage; not an official Korg product and not a component-level replica.*

| Path | Contents |
|---|---|
| `dist/ECHOLIVITY SDD-3000.amxd` | **The device.** Single self-contained file. Drop it into Live. |
| `docs/INSTALL.md` | Installation |
| `docs/MANUAL.md` | User manual |
| `docs/TEST_REPORT.md` | Test and validation report: PASS / FAIL / NOT VERIFIED (engine, static, runtime, performance, audio comparison) |
| `docs/ENGINEERING_CHANGES.md` | Engineering change report for 1.0.2 (root causes, fixes, every intentional sonic difference) |
| `docs/OUTSTANDING_ISSUES.md` | Outstanding issues |
| `docs/LIVE_VALIDATION_CHECKLIST.md` | Manual Ableton Live validation steps (not yet performed) |
| `docs/measurements/` | CPU benchmark and regression-audio measurements |
| `docs/validation/MUSICAL_EVALUATION.md` | Musical evaluation (dub material, measured): findings, strengths, proposals; audio in `audio_examples/musical_eval/` |
| `docs/validation/` | Final validation round: release decision, Live integration report (BLOCKED), DSP regression, CPU/latency, preset compatibility, defects, blocked tests |
| `docs/OUTPUT_PROTECTION.md` | Exact behaviour of the output soft-saturation curves |
| `docs/STATIC_CHECKS.json`, `docs/TEST_RESULTS.json` | Machine-readable check results |
| `docs/RESEARCH_NOTES.md` | Authentic vs. inferred vs. modern, with sources |
| `docs/ui_preview.png` | Interface layout preview |
| `CHANGELOG.md` | Changelog |
| `presets/factory_programs.json` | Factory program bank (also built into the device) |
| `audio_examples/` | 19 WAV files: the dry source (`00_dry_source.wav`) + 18 rendered demos (01–13, 14a, 14b, 15–17) |
| `audio_examples/regression/` | 8 WAV files: v1.0.1 vs v1.0.2-rc1 on identical input (HOLD release ×2, release + re-engage, invalid input) |
| `src/gen/echolivity_core.genexpr` | gen~ DSP source (exactly what is inside the device) |
| `src/max/ECHOLIVITY_SDD-3000.maxpat` | The device patcher as plain JSON |
| `tools/` | Generators: `make_gen.py` (DSP), `gen2c.py` (GenExpr→C for testing), `fit_hfcomp.py`, `build_amxd.py`, `make_report.py`; checks: `inspect_amxd.py`, `analyse_output_protection.py`, `verify_release.py` |
| `SHA256SUMS.txt` | Checksums of every file in the release |
| `docs/baseline/` | Baseline hashes of earlier releases (v1.0 core files; v1.0.1 files unchanged in 1.0.2) |
| `tests/` | Engine validation suite, example renderer, C benchmark (`bench_engine.c`), v1.0.1 reference DSP (`reference/`) |

## Rebuilding and testing (developers)

Requirements: Python 3.9+ with numpy and scipy, and a C compiler (`gcc`, or set `CC`). Tested on Linux. Running the test tools on Windows (MinGW-w64) or macOS (clang) is expected to work but is NOT VERIFIED.

```
python3 tools/make_gen.py          # regenerate the GenExpr (byte-identical to the shipped file)
python3 tools/build_amxd.py        # rebuild the .amxd (byte-identical to the shipped device)
python3 tests/run_tests.py         # 51 engine tests (incl. A/B vs v1.0.1); creates build/ automatically
python3 tools/inspect_amxd.py      # 20 static device checks
python3 tools/make_report.py       # regenerate docs/TEST_REPORT.md
python3 tools/verify_release.py    # clean-copy rebuild + determinism + audio re-render + checksums
```

`tests/run_tests.py` exits non-zero on any unexpected failure. In rc5 one known-limitation test is reported as FAIL (D-3, pre-existing start-up behaviour); the other 43 must pass.

```
python3 tools/check_compat.py "tests/reference/ECHOLIVITY SDD-3000 v1.0.1.amxd" "dist/ECHOLIVITY SDD-3000.amxd"   # parameter/preset compatibility
gcc -O2 -o bench tests/bench_engine.c -ldl && ./bench build/engine.so   # CPU grid (C build)
```

## Licence

ECHOLIVITY SDD-3000 is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License, version 3** (see `LICENSE`). It is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

Copyright (C) 2026 the ECHOLIVITY authors. Korg and SDD-3000 are trademarks of their respective owner; this project is not affiliated with or endorsed by Korg.

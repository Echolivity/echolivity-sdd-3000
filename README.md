# ECHOLIVITY SDD-3000

<p align="center">
  <strong>A digital delay for Ableton Live 12.</strong><br>
  Inspired by the character and workflow of the 1982 Korg SDD-3000.
</p>

<p align="center">
  <a href="https://github.com/Echolivity/echolivity-sdd-3000/releases">Releases</a> ·
  <a href="docs/MANUAL.md">Manual</a> ·
  <a href="docs/INSTALL.md">Installation</a> ·
  <a href="docs/validation/RELEASE_DECISION.md">Release decision</a>
</p>

<p align="center">
  <img src="docs/ui_preview.png" alt="ECHOLIVITY SDD-3000 interface preview" width="820">
</p>

> **Current build: v1.0.2-rc5 — conditional pass.**
> This is a release candidate, **not a production-ready release**. The DSP and static checks are documented, but full Ableton Live validation remains outstanding. Read the [release decision](docs/validation/RELEASE_DECISION.md) before using this build in a critical session.

## At a glance

| | |
|---|---|
| **Format** | Max for Live Audio Effect |
| **Host** | Ableton Live 12 |
| **Inspiration** | Korg SDD-3000 (1982) |
| **Build** | v1.0.2-rc5 |
| **Status** | Conditional pass · Live validation outstanding |
| **License** | GPL-3.0 |

## Get the device

**[Download the self-contained Max for Live device](dist/ECHOLIVITY%20SDD-3000.amxd)**

1. Download the .amxd file.
2. Drag it onto an audio track in Ableton Live 12.
3. Consult the [installation guide](docs/INSTALL.md) and [user manual](docs/MANUAL.md) for setup and operation.

## What’s new in rc5

- Triplet divisions added to sync.
- LOOP COMP and CAL controls added for the external loop.
- Max Console message flood fixed (UI-2).
- First owner-run Live 12 results recorded.

Recent history:
- **rc4:** fixed a blank panel in Live 12 (UI-1) and added an external regeneration loop via FB ROUTE / RETURN, using device inputs and outputs 3–4.
- **rc3:** added LFO “Mod” mapping on the 13 continuous knobs and fixed D-1 preset hot-loading.

See the [changelog](CHANGELOG.md) and [engineering change report](docs/ENGINEERING_CHANGES.md) for details.

## Project documentation

| Start here | What it covers |
|---|---|
| [User manual](docs/MANUAL.md) | Controls, operation and signal flow |
| [Installation](docs/INSTALL.md) | Installing and loading the device |
| [Release decision](docs/validation/RELEASE_DECISION.md) | Current release status and go/no-go rationale |
| [Live validation checklist](docs/LIVE_VALIDATION_CHECKLIST.md) | Manual checks still required in Ableton Live |
| [Test report](docs/TEST_REPORT.md) | Engine, static, runtime, performance and audio-comparison results |
| [Outstanding issues](docs/OUTSTANDING_ISSUES.md) | Known limitations and unresolved defects |
| [Musical evaluation](docs/validation/MUSICAL_EVALUATION.md) | Evaluation using dub material, with findings and proposals |
| [Engineering changes](docs/ENGINEERING_CHANGES.md) | Root causes, fixes and intentional sonic differences |
| [Research notes](docs/RESEARCH_NOTES.md) | Historical details: authentic, inferred and modern |
| [Output protection](docs/OUTPUT_PROTECTION.md) | Output soft-saturation behaviour |
| [Changelog](CHANGELOG.md) | Version history |

## For developers

The repository includes the GenExpr DSP source, Max patcher, build scripts, test suite, presets, measurements and audio examples.

**Requirements:** Python 3.9+ with NumPy and SciPy, plus a C compiler (gcc, or set CC). The documented toolchain has been tested on Linux. Windows (MinGW-w64) and macOS (clang) are not verified.

From the repository root:

~~~bash
python3 tools/make_gen.py
python3 tools/build_amxd.py
python3 tests/run_tests.py
python3 tools/inspect_amxd.py
python3 tools/make_report.py
python3 tools/verify_release.py
~~~

The test runner reports 51 engine tests, including A/B checks against v1.0.1. In rc5, one known-limitation test is reported as FAIL (D-3, pre-existing start-up behaviour); the other 43 are expected to pass. See the [test report](docs/TEST_REPORT.md) and [release decision](docs/validation/RELEASE_DECISION.md) for the precise status and interpretation.

Additional checks:

~~~bash
python3 tools/check_compat.py "tests/reference/ECHOLIVITY SDD-3000 v1.0.1.amxd" "dist/ECHOLIVITY SDD-3000.amxd"
gcc -O2 -o bench tests/bench_engine.c -ldl && ./bench build/engine.so
~~~

### Repository map

- dist/ — packaged Max for Live device.
- src/gen/ — GenExpr DSP source.
- src/max/ — Max patcher in JSON form.
- presets/ — factory program bank.
- tests/ — engine tests, renderer, benchmark and reference DSP.
- tools/ — generators, build utilities, reports and verification.
- audio_examples/ — rendered demonstrations and regression audio.
- docs/measurements/ and docs/validation/ — measurements and validation evidence.
- SHA256SUMS.txt — release file checksums.

## Project status and caveat

This project is an independent homage. It is **not** an official Korg product, is not endorsed by Korg, and is not a component-level replica. Korg and SDD-3000 are trademarks of their respective owner.

## License

Released under the **GNU General Public License v3.0**. See [LICENSE](LICENSE). The software is provided without warranty, including without implied warranty of merchantability or fitness for a particular purpose.

Copyright © 2026 the ECHOLIVITY authors.

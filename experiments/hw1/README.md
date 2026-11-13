# experiments/hw1 — HW-1 clock-domain spur investigation

This is an experimental harness only. Nothing in this folder is used by the device, the tests or the build. The report is in `docs/validation/HW1_INVESTIGATION.md`.

| Script | Purpose |
|---|---|
| `reproduce.py` | Production engine: reported cases, sweeps, conditions → `results/reproduction.json` |
| `convmodel.py` | Isolated numpy model of the 64 kHz conversion (production, A, B, C kernels) |
| `evaluate_candidates.py` | Model comparison → `results/candidates.json` + plots |
| `taps_tradeoff.py` | Kernel length vs rejection, passband and latency for candidate B |
| `make_bl.py` | Builds candidate B from a **copy** of the production genexpr into `build/` (gitignored) |
| `compare_bl.py` | Full-device A/B → `results/ab_full_device.json`, plots, `audio/*.flac` |
| `run_suites_bl.py` | Runs the existing engine and hw-reference suites against both engines without writing docs |

Run the scripts from the repo root, in this order:

```
python3 -c "import sys; sys.path.insert(0,'tests'); import engine; engine.build()"
python3 experiments/hw1/make_bl.py
python3 experiments/hw1/reproduce.py
python3 experiments/hw1/compare_bl.py
```

The first command is the production build (`tests/engine.py` `build()`); it must have produced `build/engine.so` before the experiment scripts run.

## Remediation phase (candidate D)

| File | Purpose |
|---|---|
| `latency_alternatives.py` | Model: 12/16/32-tap linear-phase sinc, minimum-phase FIR, analog-prototype (D) orders → `results/latency_alternatives.*` |
| `make_d.py` | Generates candidate D from a **copy** of the production genexpr (`build/echolivity_core_d.genexpr`) |
| `build_d.sh` | Generate → gen2c → .so (`build/engine_<name>.so`) |
| `fit_d.py` | Calibration (voicing EQ, TIME-0 matching biquad, latency compensation) → `d_calibration.json` |
| `run_suites_bl.py <so> <tag>` | Existing engine and hardware-reference suites against a candidate → `results/suites_production_vs_<tag>.json` |
| `run_some.py` | Selected existing tests, full detail, nothing written to `docs/` |
| `qualify_d.py` | Qualification measurements → `results/qualification_d.json`, `d_*.png` |
| `sonic_ab.py` | All 9 factory programs A/B → `results/sonic_ab.json`, `audio_d/*.flac` |
| `fb10_tail_probe.py` | FB 10 oscillation-mode offsets → `results/fb10_tail_modes.json` |
| `bench_hw1.c` | CPU grid 44.1–192 kHz → `results/cpu_bench_{prod,d}.csv` |
| `make_test_device.py` | Separate native test device `candidate/ECHOLIVITY SDD-3000 HW1-D TEST.amxd` |
| `candidate/` | The exact candidate gen~ code and test device that were qualified |

Reproduce the candidate D runs:

```
python3 experiments/hw1/fit_d.py
experiments/hw1/build_d.sh d
python3 experiments/hw1/run_suites_bl.py experiments/hw1/build/engine_d.so d
python3 experiments/hw1/qualify_d.py
python3 experiments/hw1/sonic_ab.py
```

`fit_d.py` regenerates the calibration. The committed `d_calibration.json` is the one that was qualified.

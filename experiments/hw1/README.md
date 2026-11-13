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

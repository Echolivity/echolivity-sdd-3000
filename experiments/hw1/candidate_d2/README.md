# Candidate D2: source and reproducible build

D2 is candidate D plus **one** correction: the HOLD-release switch waits for the uncompensated read offset. The full diff against D is in `D_to_D2.diff` and is a single line.

| File | sha256 |
|---|---|
| `echolivity_core_d2.genexpr` | see `../d2/results/MANIFEST.sha256` |
| `ECHOLIVITY SDD-3000 HW1-D2 TEST.amxd` (native test build; panel reads "HW1-D2 TEST") | see `../d2/results/MANIFEST.sha256` |

Candidate D stays recoverable, unchanged, in `../candidate/`: genexpr `a676f3e7…`, device `5be387cb…`.

## Rebuild from the repository (branch `candidate/hw1-d2`)

Requirements:

- Python 3 with numpy, scipy and matplotlib;
- gcc;
- optionally ffmpeg, for the FLAC renders.

```
python3 -c "import sys; sys.path.insert(0,'tests'); import engine; engine.build()"   # production + reference builds
python3 experiments/hw1/make_d.py --d2 --out experiments/hw1/candidate_d2/echolivity_core_d2.genexpr
python3 tools/gen2c.py experiments/hw1/candidate_d2/echolivity_core_d2.genexpr experiments/hw1/d2/build/engine_d2.c
gcc -O2 -shared -fPIC -o experiments/hw1/d2/build/engine_d2.so experiments/hw1/d2/build/engine_d2.c -lm
python3 experiments/hw1/make_test_device.py experiments/hw1/candidate_d2/echolivity_core_d2.genexpr HW1-D2
```

- `make_d.py` reads the production genexpr, which is never modified, and the committed `experiments/hw1/d_calibration.json`.
- `python3 experiments/hw1/fit_d.py` regenerates that calibration bit-exactly; the audit verified this.
- `make_d.py` without `--d2` regenerates candidate D. `--d2-oc` regenerates the **rejected** output-coupling variant (see `../d2/rejected_output_coupling/`).

## Regression runs (results in `experiments/hw1/d2/results/`)

```
export AUDIT_RESULTS=$PWD/experiments/hw1/d2/results
P=build/engine.so; D=experiments/hw1/audit/build/engine_cand.so; D2=experiments/hw1/d2/build/engine_d2.so
python3 tools/gen2c.py experiments/hw1/candidate/echolivity_core_d.genexpr experiments/hw1/audit/build/engine_cand.c && gcc -O2 -shared -fPIC -o $D experiments/hw1/audit/build/engine_cand.c -lm
python3 experiments/hw1/audit/audit_suites.py production=$P candidate_D=$D candidate_D2=$D2      # full original suite
python3 experiments/hw1/audit/audit_hold.py production=$P candidate_D=$D candidate_D2=$D2        # 225 HOLD cases
python3 experiments/hw1/audit/audit_fb10.py production=$P candidate_D=$D candidate_D2=$D2        # FB 10, 30 seeds
python3 experiments/hw1/audit/audit_spectral.py production=$P candidate_D=$D candidate_D2=$D2
python3 experiments/hw1/audit/audit_timing.py production=$P candidate_D=$D candidate_D2=$D2
python3 experiments/hw1/audit/audit_programs.py production=$P candidate_D=$D candidate_D2=$D2
python3 experiments/hw1/d2/bitident_d_vs_d2.py
python3 experiments/hw1/run_suites_bl.py $D2 d2                                                   # hardware-reference suite
gcc -O2 -o bench_pct experiments/hw1/audit/bench_pct.c -ldl && ./bench_pct $P $D2                 # CPU (interleaved)
python3 experiments/hw1/d2/fb10_mechanism.py; python3 experiments/hw1/d2/fb10_hf_diag.py; python3 experiments/hw1/d2/fb10_dither_diag.py
```

Nothing writes to `docs/`, `src/`, `tests/`, `tools/`, `presets/` or `dist/`.

Exception: `tools/check_compat.py` always writes `docs/validation/PRESET_COMPATIBILITY.json`. Restore that file with `git checkout` after running it; a copy of its output is kept in `d2/results/`.

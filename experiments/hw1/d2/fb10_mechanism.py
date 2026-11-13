#!/usr/bin/env python3
"""D2 investigation of the FB 10 TRUE STEREO tail offset (diagnostic; no DSP change).
1. Seeding: the offset only appears when the excitation carries DC (t_feedback_extreme feeds L with
   uniform noise + 0.5).
2. Restoring force: start a symmetric self-oscillation (no input DC), inject a 50 ms DC-offset burst at
   6 s, then silence; track the output mean in 1 s windows for 16 s. A loop with a restoring force on the
   duty cycle returns to ~0; a neutral loop keeps the injected offset.
3. Duty cycle: fraction of memory words > 0 (probe dv_l) vs output mean.
-> results/fb10_mechanism.json"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from engine import Engine
sr = 48000
E = {"production": os.path.join(ROOT, "build", "engine.so"), "candidate_D": os.path.join(ROOT, "experiments/hw1/audit/build/engine_cand.so")}
P = dict(time_ms=37, feedback=10, balance=10, in_range=0, in_level=10, out_mode=3, waveform=2, intensity=10, frequency=8)
res = {"seeding": {}, "perturbation": {}, "duty": {}}


def run(so, xl, xr, **p):
    e = Engine(sr, so=so, **dict(P, **p)); return e.run(xl, xr)


for name, so in E.items():
    for dc in (-0.5, 0.0, 0.5):
        vals = []
        for seed in range(100, 112):
            rng = np.random.default_rng(seed)
            xl = np.concatenate([rng.uniform(-1, 1, sr * 4) + dc, np.zeros(sr * 8)])
            y = run(so, xl, rng.uniform(-1, 1, len(xl)))
            vals.append(float(y[0][-2 * sr:].mean()))
        res["seeding"][f"{name}|input_dc={dc}"] = dict(values=vals, median_abs=float(np.median(np.abs(vals))),
                                                       n_over_0p003=int(np.sum(np.abs(vals) > 0.003)), mean=float(np.mean(vals)))
        print("seed", name, dc, res["seeding"][f"{name}|input_dc={dc}"]["n_over_0p003"], "/12 mean %+.4f" % np.mean(vals), flush=True)
    traces = []
    for seed in range(100, 108):
        rng = np.random.default_rng(seed)
        n = sr * 22
        xl = np.zeros(n); xr = np.zeros(n)
        xl[:sr * 4] = rng.uniform(-1, 1, sr * 4); xr[:sr * 4] = rng.uniform(-1, 1, sr * 4)
        xl[sr * 6:sr * 6 + sr // 20] += 0.5                       # DC burst into the running oscillation
        y = run(so, xl, xr)
        traces.append([float(y[0][i * sr:(i + 1) * sr].mean()) for i in range(22)])
    res["perturbation"][name] = traces
    tr = np.array(traces)
    print("perturb", name, "mean |offset| s5 %.4f s7 %.4f s10 %.4f s15 %.4f s21 %.4f" % tuple(np.mean(np.abs(tr[:, k])) for k in (5, 7, 10, 15, 21)), flush=True)
json.dump(res, open(os.path.join(HERE, "results", "fb10_mechanism.json"), "w"), indent=1)

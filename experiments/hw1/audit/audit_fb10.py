#!/usr/bin/env python3
"""Audit B (FB 10 tail statistic): the exact t_feedback_extreme combination (TRUE STEREO, RND INT 10,
FREQ 8, FB 10, 37 ms) with 30 seeds per engine; |mean of last 2 s| per channel and whether the offset grows.
-> results/audit_fb10.json"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from engine import Engine
engs = dict(a.split("=", 1) for a in sys.argv[1:]); sr = 48000; res = {}
for name, so in engs.items():
    vals, growth = [], []
    for seed in range(100, 130):
        rng = np.random.default_rng(seed)
        e = Engine(sr, so=os.path.abspath(so), time_ms=37, feedback=10, balance=10, in_range=0, in_level=10, out_mode=3, waveform=2, intensity=10, frequency=8)
        x = np.concatenate([rng.uniform(-1, 1, sr * 4) + 0.5, np.zeros(sr * 8)])
        y = e.run(x, rng.uniform(-1, 1, len(x)))
        tail = max(abs(np.mean(y[0][-sr * 2:])), abs(np.mean(y[1][-sr * 2:])))
        early = max(abs(np.mean(y[0][-sr * 6:-sr * 4])), abs(np.mean(y[1][-sr * 6:-sr * 4])))
        vals.append(float(tail)); growth.append(float(tail - early))
    v = np.array(vals)
    res[name] = dict(n=len(v), median=float(np.median(v)), p90=float(np.percentile(v, 90)), max=float(v.max()),
                     n_over_test_limit_0p003=int((v > 0.003).sum()), mean_growth_last4s=float(np.mean(growth)), values=vals)
    print(name, {k: res[name][k] for k in ("median", "p90", "max", "n_over_test_limit_0p003", "mean_growth_last4s")}, flush=True)
json.dump(res, open(os.path.join(os.environ.get("AUDIT_RESULTS", os.path.join(HERE, "results")), "audit_fb10.json"), "w"), indent=1)

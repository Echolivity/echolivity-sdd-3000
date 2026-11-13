#!/usr/bin/env python3
"""Diagnostic: dependence of the FB 10 tail offset on loop high-frequency gain (HIGH cut 8 kHz) and on the
clock modulation (RND INT 10 vs off), production vs D2. 12 seeds, input DC +0.5. -> results/fb10_hf_diag.json"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from engine import Engine
sr = 48000
E = {"production": os.path.join(ROOT, "build/engine.so"), "candidate_D2": os.path.join(HERE, "build/engine_d2.so")}
CASES = {"test case (HIGH flat, RND INT10)": dict(), "HIGH 8 kHz": dict(highcut=1), "HIGH 4 kHz": dict(highcut=2),
         "modulation off": dict(intensity=0), "SQUARE INT10": dict(waveform=1)}
res = {}
for cname, extra in CASES.items():
    for name, so in E.items():
        m, zc = [], []
        for seed in range(100, 112):
            rng = np.random.default_rng(seed)
            p = dict(time_ms=37, feedback=10, balance=10, in_range=0, in_level=10, out_mode=3, waveform=2, intensity=10, frequency=8); p.update(extra)
            e = Engine(sr, so=so, **p)
            x = np.concatenate([rng.uniform(-1, 1, sr * 4) + 0.5, np.zeros(sr * 8)])
            y = e.run(x, rng.uniform(-1, 1, len(x)))[0]
            m.append(float(abs(y[-2 * sr:].mean()))); s = y[6 * sr:8 * sr]; zc.append(float(np.sum(np.diff(np.sign(s)) != 0) / 4))
        res[f"{cname}|{name}"] = dict(n_over_0p003=int(np.sum(np.array(m) > 0.003)), median_abs=float(np.median(m)), max_abs=float(np.max(m)), median_zc=float(np.median(zc)))
        print(cname, name, res[f"{cname}|{name}"], flush=True)
json.dump(res, open(os.path.join(HERE, "results", "fb10_hf_diag.json"), "w"), indent=1)

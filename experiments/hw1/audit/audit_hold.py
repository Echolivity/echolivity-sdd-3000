#!/usr/bin/env python3
"""Audit A: HOLD release timing, production vs candidate D (and an isolated counterfactual build).
For every case: first sample where 'released' differs from 'HOLD kept' (> -180 dB re peak), compared with
the contract t_sw = min(T, 943.9 ms). Uses tests/run_tests.hold_release_case unmodified.
Usage: audit_hold.py name=engine.so [name=engine.so ...]  -> results/audit_hold.json"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import engine, run_tests as RT
OUT = os.path.join(HERE, "results"); os.makedirs(OUT, exist_ok=True)
engs = dict(a.split("=", 1) for a in sys.argv[1:])
Ts = (0, 1, 2, 3, 5, 10, 16, 50, 120, 380, 700, 1000, 1008, 1016, 1023)
res = {}
for name, so in engs.items():
    engine.SO = os.path.abspath(so)
    rows = []
    for sr in (44100, 48000, 88200, 96000, 192000):
        for mode in (0, 1):
            for T in Ts:
                R, K, N = RT.hold_release_case(sr, T, mode)
                for ch in range(2 if mode else 1):
                    r, k = R[ch], K[ch]
                    diff = np.nonzero(np.abs(r - k) > 1e-9 * np.max(np.abs(k)))[0]
                    first = diff[0] / sr * 1000 if len(diff) else 1e9
                    t_sw = min(T, 943.9)
                    rows.append(dict(sr=sr, mode="TS" if mode else "MONO", T=T, ch=ch, first_diff_ms=round(first, 4),
                                     early_ms=round(max(0.0, t_sw - first), 4), test_criterion_pass=bool(first >= t_sw - 0.05),
                                     strict_pass=bool(first >= t_sw - 0.5 / sr * 1000)))
        print(name, sr, "worst early %.4f ms" % max(x["early_ms"] for x in rows if x["sr"] == sr), flush=True)
    res[name] = dict(rows=rows, worst_early_ms=max(x["early_ms"] for x in rows),
                     n=len(rows), n_fail_test_criterion=sum(not x["test_criterion_pass"] for x in rows),
                     n_fail_strict=sum(not x["strict_pass"] for x in rows))
    print(name, {k: v for k, v in res[name].items() if k != "rows"}, flush=True)
json.dump(res, open(os.path.join(OUT, os.environ.get("AUDIT_OUT", "audit_hold.json")), "w"), indent=1)

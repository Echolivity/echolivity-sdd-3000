#!/usr/bin/env python3
"""Audit D: timing. Echo position of an impulse with the test's amplitude (0.5: overloads the converter)
and with a linear-range amplitude (0.005), TIME 0..1023 ms, 44.1/48/96 kHz; latency vs TIME in continuous
mode below 1 ms (short-path boundary); block-size independence (vector 1, 7, 64, 256) of the output;
fresh-instance first-50-ms output. -> results/audit_timing.json"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from engine import Engine
engs = dict(a.split("=", 1) for a in sys.argv[1:])


def echo(so, sr, T, amp, **p):
    e = Engine(sr, so=so, time_ms=T, feedback=0, balance=10, **p)
    e.silence(1.2)
    n = int(sr * (T / 1000 + 0.2)); x = np.zeros(n); x[0] = amp
    y = e.run(x)[0]
    i = int(np.argmax(np.abs(y)))
    a, b, c = y[i - 1], y[i], y[i + 1]; den = a - 2 * b + c
    return (i + (0.5 * (a - c) / den if den else 0)) / sr * 1000


res = {}
for name, so in engs.items():
    so = os.path.abspath(so); r = {}
    for sr in (44100, 48000, 96000):
        for amp in (0.5, 0.005):
            b = echo(so, sr, 0, amp)
            r[f"{sr}|amp{amp}"] = dict(time0_ms=round(b, 4), err_us={T: round((echo(so, sr, T, amp) - T) * 1000, 2) for T in (1, 2, 10, 100, 1023)})
        # continuous-mode TIME below 1 ms: echo position vs requested (short-path / memory-path boundary)
        r[f"{sr}|continuous"] = {str(T): round(echo(so, sr, T, 0.005, time_mode=1), 4) for T in (0.0, 0.05, 0.09, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0)}
    # block-size independence: identical output for different vector sizes (automation-free)
    outs = {}
    for vec in (1, 7, 64, 256):
        Engine.VEC = vec
        e = Engine(48000, so=so, time_ms=120, feedback=6, intensity=3, frequency=4, balance=5)
        x = np.random.default_rng(3).uniform(-0.2, 0.2, 48000)
        outs[vec] = e.run(x)[:2]
    Engine.VEC = 64
    r["block_size_max_abs_diff_vs_64"] = {str(v): float(np.max(np.abs(outs[v] - outs[64]))) for v in outs}
    # fresh instance, effect only, TIME default: first 50 ms output level re input
    e = Engine(48000, so=so, balance=10)
    x = 0.1 * np.sin(2 * np.pi * 440 * np.arange(4800) / 48000)
    y = e.run(x)[0]
    r["startup_first_50ms_db_re_input"] = round(float(20 * np.log10(np.sqrt(np.mean(y[:2400] ** 2)) / np.sqrt(np.mean(x[:2400] ** 2)) + 1e-30)), 1)
    res[name] = r
    print(name, json.dumps(r)[:1500], flush=True)
json.dump(res, open(os.path.join(os.environ.get("AUDIT_RESULTS", os.path.join(HERE, "results")), "audit_timing.json"), "w"), indent=1)

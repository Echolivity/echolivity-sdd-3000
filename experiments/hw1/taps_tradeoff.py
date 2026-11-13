#!/usr/bin/env python3
"""Candidate B: kernel length vs image rejection / passband / latency (isolated model)."""
import json, os
import numpy as np
import convmodel as C
from reproduce import spurs, spectrum, db
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
F_IN = [1000, 5000, 10000, 12000, 14000, 15000, 16000, 17000]


def audible_worst(name, fs, taps, fc):
    worst = (None, -999.0, None)
    for f0 in F_IN:
        x = 0.01 * np.sin(2 * np.pi * f0 * np.arange(fs) / fs)
        y = C.run_candidate(name, x, fs, taps=taps, fc_hz=fc)[fs // 2:]
        fr, S = spectrum(y, fs)
        k0 = np.argmin(np.abs(fr - f0)); a0 = S[k0 - 3:k0 + 4].max()
        m = (np.abs(fr - f0) > 25) & (fr > 15) & (fr <= 20000)
        k = np.argmax(S * m)
        r = float(db(S[k] / a0))
        if r > worst[1]:
            worst = (f0, r, float(fr[k]))
    return worst


def gain(name, fs, f0, taps, fc):
    x = 0.01 * np.sin(2 * np.pi * f0 * np.arange(fs) / fs)
    y = C.run_candidate(name, x, fs, taps=taps, fc_hz=fc)[fs // 2:]
    fr, S = spectrum(y, fs)
    return float(db(S[np.argmin(np.abs(fr - f0))] / 0.01))


rows = []
for fs in (44100, 48000, 96000):
    fc = 19000.0 if fs < 46000 else 20000.0
    for taps in (8, 12, 16, 24, 32):
        w = audible_worst("B_bandlimited", fs, taps, fc)
        g1 = gain("B_bandlimited", fs, 1000, taps, fc)
        rows.append(dict(host=fs, taps=taps, fc_hz=fc, worst_audible_spur_db=round(w[1], 1), at_input_hz=w[0], spur_hz=w[2],
                         g15k_db=round(gain("B_bandlimited", fs, 15000, taps, fc) - g1, 2),
                         g17k_db=round(gain("B_bandlimited", fs, 17000, taps, fc) - g1, 2),
                         latency_ms=round(taps / fs * 1000, 3)))
        print(rows[-1])
    w = audible_worst("production", fs, 0, 0)
    rows.append(dict(host=fs, taps="production", worst_audible_spur_db=round(w[1], 1), at_input_hz=w[0], spur_hz=w[2]))
    print(rows[-1])
json.dump(rows, open(os.path.join(OUT, "taps_tradeoff.json"), "w"), indent=1)

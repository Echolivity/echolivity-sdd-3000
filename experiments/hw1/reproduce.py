#!/usr/bin/env python3
"""
HW-1 investigation, step 1: independent reproduction on the PRODUCTION engine
(C build of src/gen/echolivity_core.genexpr; nothing modified).

Writes experiments/hw1/results/reproduction.json.
"""
import json, os, sys
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from engine import Engine, build  # noqa: E402

NOM = 10 ** (-17 / 20)
OUT = os.path.join(HERE, "results")


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-30))


def spectrum(y, sr):
    w = signal.windows.blackmanharris(len(y))
    S = np.abs(np.fft.rfft(y * w)) / (w.sum() / 2)          # peak amplitude scaling
    return np.fft.rfftfreq(len(y), 1 / sr), S


def spurs(y, sr, f0, n=5, floor_db=-140):
    fr, S = spectrum(y, sr)
    k0 = int(np.argmin(np.abs(fr - f0)))
    a0 = S[k0 - 3:k0 + 4].max()
    m = (np.abs(fr - f0) > 25) & (fr > 15)
    out, S2 = [], S * m
    for _ in range(n):
        k = int(np.argmax(S2))
        if S2[k] <= 0 or db(S2[k] / a0) < floor_db:
            break
        out.append((float(round(fr[k], 1)), float(round(db(S2[k] / a0), 1))))
        S2[max(k - 6, 0):k + 7] = 0
    return float(db(a0)), out


def run(sr, x, **p):
    e = Engine(sr, **p)
    e.silence(0.1)
    return e.run(x)[0]


def main():
    build()
    res = dict(engine="production C build of src/gen/echolivity_core.genexpr", cases=[], sweep=[], conditions=[])
    secs = 1.0
    # 1. the four reported cases (CLEAN converter, PRE off, -20 dB re nominal: linear operating point)
    for sr, f0 in ((48000, 17000), (48000, 15000), (44100, 1000), (44100, 17000)):
        x = np.sin(2 * np.pi * f0 * np.arange(int(secs * sr)) / sr) * NOM * 0.1
        y = run(sr, x, time_ms=0, feedback=0, balance=10, converter=1, pre_on=0)[int(0.5 * sr):]
        a0, sp = spurs(y, sr, f0)
        res["cases"].append(dict(host=sr, f_in=f0, wanted_dbfs=round(a0, 2), spurs=sp))
        print(sr, f0, round(a0, 1), sp[:3])
    # 2. sweep 100 Hz - 20 kHz at 44.1 / 48 / 96 kHz
    freqs = [100, 200, 500, 1000, 2000, 3000, 5000, 7000, 8000, 10000, 12000, 14000, 15000, 16000, 17000, 18000, 19000, 20000]
    for sr in (44100, 48000, 96000):
        for f0 in freqs:
            if f0 >= sr / 2 - 300:
                continue
            x = np.sin(2 * np.pi * f0 * np.arange(int(secs * sr)) / sr) * NOM * 0.1
            y = run(sr, x, time_ms=0, feedback=0, balance=10, converter=1, pre_on=0)[int(0.5 * sr):]
            a0, sp = spurs(y, sr, f0, n=3)
            res["sweep"].append(dict(host=sr, f_in=f0, wanted_dbfs=round(a0, 2), top_spur=sp[0] if sp else None, spurs=sp))
    # 3. conditions at 48 kHz, 10 kHz and 17 kHz tones
    conds = [("direct path (BAL 0)", dict(balance=0, converter=1, pre_on=0)),
             ("delayed TIME 0, CLEAN, PRE off", dict(time_ms=0, feedback=0, balance=10, converter=1, pre_on=0)),
             ("delayed TIME 250", dict(time_ms=250, feedback=0, balance=10, converter=1, pre_on=0)),
             ("13-bit converter, PRE on (default character)", dict(time_ms=0, feedback=0, balance=10)),
             ("feedback 5 (TIME 50)", dict(time_ms=50, feedback=5, balance=10, converter=1, pre_on=0)),
             ("modulation INT 2 TRI 0.45 Hz", dict(time_ms=100, feedback=0, balance=10, converter=1, pre_on=0, intensity=2, frequency=3)),
             ("level -40 dB re nominal", dict(time_ms=0, feedback=0, balance=10, converter=1, pre_on=0, _amp=0.01)),
             ("level nominal", dict(time_ms=0, feedback=0, balance=10, converter=1, pre_on=0, _amp=1.0)),
             ("HF comp off (engineering switch)", dict(time_ms=0, feedback=0, balance=10, converter=1, pre_on=0, hf_comp=0))]
    for sr in (48000, 44100, 96000):
        for name, p in conds:
            p = dict(p)
            amp = p.pop("_amp", 0.1)
            for f0 in (10000, 17000):
                x = np.sin(2 * np.pi * f0 * np.arange(int(2.0 * sr)) / sr) * NOM * amp
                y = run(sr, x, **p)[int(1.0 * sr):]
                a0, sp = spurs(y, sr, f0, n=3)
                res["conditions"].append(dict(host=sr, condition=name, f_in=f0, wanted_dbfs=round(a0, 2), spurs=sp))
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "reproduction.json"), "w"), indent=1)


if __name__ == "__main__":
    main()

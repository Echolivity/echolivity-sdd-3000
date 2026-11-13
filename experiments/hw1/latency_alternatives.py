#!/usr/bin/env python3
"""
HW-1 remediation, step 1: latency alternatives on the isolated conversion model.
Compares production, linear-phase band-limited FIR kernels (12/16/32 taps), a minimum-phase FIR
kernel, and candidate D (continuous-time analog-prototype conversion, several orders).
Writes results/latency_alternatives.json and results/latency_alternatives.png.
"""
import json, os
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import convmodel as C
from reproduce import spurs, spectrum, db
from evaluate_candidates import quant13

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")
SWEEP = [100, 500, 1000, 2000, 5000, 8000, 10000, 12000, 15000, 16000, 17000, 18000, 19000, 20000]
RATES = (44100, 48000, 96000)
AMP = 0.01

D_CHOSEN = dict(order=7, rp=0.05, rs=90.0, fp_hz=21000.0, extra_poles_hz=(50000.0, 70000.0))
CANDS = {
    "production": lambda x, fs, mod=None, q=None: C.run_candidate("production", x, fs, mod=mod, quant=q),
    "B_linear_32": lambda x, fs, mod=None, q=None: C.run_candidate("B_bandlimited", x, fs, mod=mod, quant=q, taps=32),
    "B_linear_16": lambda x, fs, mod=None, q=None: C.run_candidate("B_bandlimited", x, fs, mod=mod, quant=q, taps=16),
    "B_linear_12": lambda x, fs, mod=None, q=None: C.run_candidate("B_bandlimited", x, fs, mod=mod, quant=q, taps=12),
    "B_minphase_16": lambda x, fs, mod=None, q=None: C.run_B_minphase(x, fs, 16, mod=mod, quant=q),
    "D_ellip5": lambda x, fs, mod=None, q=None: C.run_D(x, fs, mod=mod, quant=q, proto=C.analog_proto(5, 0.05, 70, 20000, extra_poles_hz=(50000,))),
    "D_ellip7": lambda x, fs, mod=None, q=None: C.run_D(x, fs, mod=mod, quant=q, proto=C.analog_proto(**D_CHOSEN)),
    "D_ellip9": lambda x, fs, mod=None, q=None: C.run_D(x, fs, mod=mod, quant=q, proto=C.analog_proto(9, 0.05, 100, 21000, extra_poles_hz=(60000,))),
}
OPS = {  # rough multiply-adds per host sample per channel at 48 kHz (1.33 ticks / host sample)
    "production": 5, "B_linear_32": 256, "B_linear_16": 128, "B_linear_12": 96, "B_minphase_16": 128,
    "D_ellip5": 4 * 2 * 1.33 * 8 + 8, "D_ellip7": 6 * 2 * 1.33 * 8 + 12, "D_ellip9": 6 * 2 * 1.33 * 8 + 12,
}


def tone(f, fs, secs=1.0):
    return AMP * np.sin(2 * np.pi * f * np.arange(int(secs * fs)) / fs)


def worst(run, fs):
    w = (None, None, -999.0)
    for f0 in SWEEP:
        if f0 > fs / 2 - 1500:
            continue
        y = run(tone(f0, fs), fs)[fs // 2:]   # quantiser off: its harmonics at this level would mask the images
        _, sp = spurs(y, fs, f0, n=1, floor_db=-200)
        if sp and sp[0][1] > w[2]:
            w = (f0, sp[0][0], sp[0][1])
    return w


def passband(run, fs):
    g = {}
    for f0 in (1000, 10000, 15000, 17000, 20000):
        y = run(tone(f0, fs), fs)[fs // 2:]
        fr, S = spectrum(y, fs)
        g[f0] = float(db(S[np.argmin(np.abs(fr - f0))] / AMP))
    return {k: round(v - g[1000], 2) for k, v in g.items()}


def timing(run, fs):
    """Impulse response of the core: peak position and energy centroid (ms), plus the group
    delay at 1 kHz and 10 kHz from the transfer function (ms)."""
    n = fs // 4
    x = np.zeros(n); x[2000] = 1.0
    y = run(x, fs)
    seg = y[2000 - 50: 2000 + 400]
    peak = (np.argmax(np.abs(seg)) - 50) / fs * 1000
    e = seg ** 2
    centroid = (np.sum(e * (np.arange(len(seg)) - 50)) / e.sum()) / fs * 1000
    H = np.fft.rfft(y[2000:2000 + 4096]); fr = np.fft.rfftfreq(4096, 1 / fs)
    ph = np.unwrap(np.angle(H)); gd = -np.gradient(ph, 2 * np.pi * fr) * 1000
    pick = lambda f: float(np.interp(f, fr, gd))
    return dict(peak_ms=round(peak, 4), centroid_ms=round(centroid, 4), gd_1k_ms=round(pick(1000), 4),
                gd_10k_ms=round(pick(10000), 4), gd_17k_ms=round(pick(17000), 4))


def modulated(run, fs, f0=17000):
    secs = 3.0
    n = int(secs * fs)
    tri = signal.sawtooth(2 * np.pi * 0.45 * np.arange(n) / fs, 0.5) * 0.5 + 0.5
    y = run(tone(f0, fs, secs), fs, mod=64000 * (1 + 0.2 * tri))[fs:]
    fr, S = spectrum(y, fs)
    P = S ** 2
    band = np.abs(fr - f0) < 400
    return round(float(10 * np.log10(P[~band & (fr > 20)].sum() / P[band].sum())), 1)


def main():
    res = {}
    for name, run in CANDS.items():
        r = {"worst_spur": {}, "ops_per_sample_est": OPS[name]}
        for fs in RATES:
            f0, fsp, lv = worst(run, fs)
            r["worst_spur"][str(fs)] = dict(tone_hz=f0, spur_hz=fsp, db=lv)
        r["passband_48k_re_1k"] = passband(run, 48000)
        r["timing_48k"] = timing(run, 48000)
        r["modulated_17k_48k_db"] = modulated(run, 48000)
        res[name] = r
        print(name, {k: v["db"] for k, v in r["worst_spur"].items()}, r["timing_48k"], r["passband_48k_re_1k"], r["modulated_17k_48k_db"], flush=True)
    res["_notes"] = {
        "model": "isolated conversion core (convmodel.py), quantiser off for the spur sweep (12-bit harmonics of a -40 dB tone would dominate), no host-rate filters/emphasis",
        "D_chosen": {k: list(v) if isinstance(v, tuple) else v for k, v in D_CHOSEN.items()},
        "timing": "peak and centroid of the core impulse response; gd = group delay from its transfer function",
    }
    json.dump(res, open(os.path.join(OUT, "latency_alternatives.json"), "w"), indent=1)
    names = [k for k in CANDS]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    for i, fs in enumerate(RATES):
        ax[0].bar(np.arange(len(names)) + (i - 1) * 0.27, [res[n]["worst_spur"][str(fs)]["db"] for n in names], 0.27, label=f"{fs/1000:g} kHz")
    ax[0].set_xticks(range(len(names))); ax[0].set_xticklabels(names, rotation=35, ha="right", fontsize=8)
    ax[0].set_ylabel("worst spur re tone (dB)"); ax[0].legend(); ax[0].set_title("Spur rejection (sweep 100 Hz-20 kHz)")
    ax[1].bar(range(len(names)), [res[n]["timing_48k"]["gd_1k_ms"] for n in names], color="#888")
    ax[1].set_xticks(range(len(names))); ax[1].set_xticklabels(names, rotation=35, ha="right", fontsize=8)
    ax[1].set_ylabel("core group delay at 1 kHz (ms)"); ax[1].set_title("Added latency (48 kHz)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "latency_alternatives.png"), dpi=110)


if __name__ == "__main__":
    main()

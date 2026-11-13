#!/usr/bin/env python3
"""Audit C plots from results/audit_spectral.json, plus raw spectra of the original defect case."""
import json, os, sys
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests")); sys.path.insert(0, HERE)
from engine import Engine
from audit_spectral import spec, NOM
R = json.load(open(os.path.join(HERE, "results", "audit_spectral.json")))
F = [100, 1000, 5000, 10000, 15000, 17000, 19000]
fig, axs = plt.subplots(2, 3, figsize=(16, 8), sharey=True)
for j, sr in enumerate((44100, 48000, 96000)):
    for i, op in enumerate(("clean", "default")):
        ax = axs[i, j]
        for eng, c in (("production", "C0"), ("candidate_D", "C1")):
            for T, ls in ((20, "-"), (0, "--")):
                for lv, mk in ((-20, "o"), (-6, "s")):
                    y = [R[eng]["tones"][f"{sr}|T{T}|{op}|{lv}|{f}"]["worst_inharmonic"]["db"] for f in F]
                    ax.plot(F, y, ls, marker=mk, ms=3, color=c, label=f"{eng} T{T} {lv} dB" if (i, j) == (0, 0) else None)
        ax.set_xscale("log"); ax.set_ylim(-180, 0); ax.grid(alpha=.3); ax.set_title(f"{sr/1000:g} kHz, {op}")
    axs[1, j].set_xlabel("tone (Hz)")
axs[0, 0].set_ylabel("worst inharmonic line re tone (dB)"); axs[1, 0].set_ylabel("worst inharmonic line re tone (dB)")
fig.legend(loc="lower center", ncol=4, fontsize=8); fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(os.path.join(HERE, "results", "audit_inharmonic.png"), dpi=100)
# group delay
fig, ax = plt.subplots(figsize=(8, 4))
for sr, ls in (("44100", ":"), ("48000", "-"), ("96000", "--")):
    for eng, c in (("production", "C0"), ("candidate_D", "C1")):
        g = R[eng]["phase_group_delay_ms"][sr]
        ax.plot([int(k) for k in g], list(g.values()), ls, color=c, label=f"{eng} {sr}")
ax.set_xscale("log"); ax.set_xlabel("Hz"); ax.set_ylabel("group delay re TIME (ms)"); ax.grid(alpha=.3); ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "results", "audit_group_delay.png"), dpi=100)
# raw spectra, 48 kHz, 17 kHz at -20 dB re nominal, defaults, TIME 20 and TIME 0
engs = {"production": os.path.join(ROOT, "build", "engine.so"), "candidate_D": os.path.join(HERE, "build", "engine_cand.so")}
fig, axs = plt.subplots(1, 2, figsize=(15, 4.5), sharey=True)
for ax, T in zip(axs, (20, 0)):
    for eng, so in engs.items():
        e = Engine(48000, so=so, time_ms=T, feedback=0, balance=10); e.silence(0.1)
        y = e.run(NOM * 0.1 * np.sin(2 * np.pi * 17000 * np.arange(60000) / 48000))[0][12000:]
        fr, S = spec(y, 48000); ax.plot(fr, 20 * np.log10(S + 1e-12), lw=.6, label=eng)
    ax.set_title(f"48 kHz, 17 kHz tone, -20 dB re nominal, 13-bit + PRE (defaults), TIME {T}")
    ax.set_xlim(0, 24000); ax.set_ylim(-200, -20); ax.grid(alpha=.3); ax.set_xlabel("Hz")
axs[0].set_ylabel("dBFS (peak-scaled)"); axs[0].legend()
fig.tight_layout(); fig.savefig(os.path.join(HERE, "results", "audit_spectrum_17k_48k.png"), dpi=100)
print("ok")

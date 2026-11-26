"""Renders the README measurement plots into docs/img/ from the C build of the shipped gen~ code.

Usage: python tools/make_readme_plots.py   (needs gcc, numpy, scipy, matplotlib)
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import spectrogram

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import engine  # noqa: E402

OUT = os.path.join(ROOT, "docs", "img")
os.makedirs(OUT, exist_ok=True)
if not os.path.exists(engine.SO):
    engine.build()
SR = 48000
BG, PANEL, INK, SUB, AMBER, CYAN, RED = "#141518", "#1d1f24", "#ecebe6", "#9aa0a8", "#f0a33a", "#5fc7d6", "#e2553f"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": SUB, "xtick.color": SUB,
                     "ytick.color": SUB, "axes.edgecolor": SUB, "axes.facecolor": PANEL, "figure.facecolor": BG,
                     "savefig.facecolor": BG, "font.size": 11})


def finish(ax, fig, name, title, note):
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", pad=12)
    for s in ax.spines.values():
        s.set_alpha(0.35)
    fig.text(0.01, 0.01, note, fontsize=8.5, color=SUB)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(OUT, name), dpi=110)
    plt.close(fig)


def wet(params, x):
    e = engine.Engine(SR, **dict(params, wet_only=1, out_mode=0))
    return e.run(x)[0]


# 1. filters in the regeneration loop: each repeat darker and thinner
x = np.zeros(int(SR * 3.2)); x[100] = 0.5
y = wet({"time_ms": 250, "feedback": 6, "lowcut": 3, "highcut": 3}, x)
f, t, S = spectrogram(y, SR, nperseg=2048, noverlap=1792)
fig, ax = plt.subplots(figsize=(10, 4.2))
Sd = 10 * np.log10(S + 1e-16); Sd -= Sd.max()
m = ax.pcolormesh(t, f / 1000, Sd, vmin=-60, vmax=0, cmap="magma", shading="auto")
ax.set_ylim(0, 12); ax.set_xlabel("Time (s)"); ax.set_ylabel("Frequency (kHz)")
cb = fig.colorbar(m, ax=ax, pad=0.01); cb.set_label("dB", color=SUB)
finish(ax, fig, "regen_filters.png", "Filters in the regeneration loop: every repeat changes tone",
       "One click in, wet only. TIME 250 ms, FEEDBACK 6, LOW 500 Hz, HIGH 2 kHz. Rendered from the C build of the shipped gen~ code.")

# 2. self-oscillation stays bounded
x = np.zeros(int(SR * 8)); x[: SR // 10] = 0.3 * np.sin(2 * np.pi * 220 * np.arange(SR // 10) / SR)
fig, ax = plt.subplots(figsize=(10, 4.2))
for fb, c, lab in [(5, CYAN, "FEEDBACK 5"), (8, AMBER, "FEEDBACK 8"), (10, RED, "FEEDBACK 10")]:
    yy = wet({"time_ms": 330, "feedback": fb}, x)
    w = int(0.05 * SR); env = np.sqrt(np.convolve(yy ** 2, np.ones(w) / w, mode="same"))
    ax.plot(np.arange(len(env)) / SR, 20 * np.log10(env + 1e-9), color=c, lw=2, label=lab)
ax.set_ylim(-80, 6); ax.set_xlim(0, 8)
ax.set_xlabel("Time (s)"); ax.set_ylabel("Level (dBFS, 50 ms RMS)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), frameon=False, ncol=3, fontsize=10)
finish(ax, fig, "self_oscillation.png", "Past 7 the repeats stop dying away, and the level stays capped",
       "A 100 ms 220 Hz burst, TIME 330 ms, wet only, default HARD saturation. Rendered from the C build of the shipped gen~ code.")
print("wrote", sorted(n for n in os.listdir(OUT) if n.endswith(".png")))

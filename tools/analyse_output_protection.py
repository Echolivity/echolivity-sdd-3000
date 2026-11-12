#!/usr/bin/env python3
"""Measure the two output-stage curves of the (unchanged) v1.0 DSP. Prints Markdown tables.

  ceiling(v) = v / (1 + (|v|/4)^8)^(1/8)          final safety ceiling, always active
  opamp(v)   = v / (1 + |v|^5)^(1/5)              output-amp rail model, scaled by PRE (character)
Both are memoryless (instantaneous) waveshapers -- no look-ahead, no gain-reduction envelope.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests"))

ceiling = lambda v: v / (1 + (np.abs(v) / 4) ** 8) ** 0.125
opamp = lambda v: v / (1 + np.abs(v) ** 5) ** 0.2


def thd(f, peak):
    n, k = 48000, 100
    x = peak * np.sin(2 * np.pi * k * np.arange(n) / n)
    F = np.abs(np.fft.rfft(f(x)))
    return 20 * np.log10(np.sqrt(np.sum(F[2 * k::k][:20] ** 2)) / F[k] + 1e-300)


def table(f, name):
    print(f"\n| {name}: input peak | output peak | gain change | THD (sine) |\n|---|---|---|---|")
    for dbfs in (-6, 0, 3, 6, 9, 12, 18, 24, 40):
        v = 10 ** (dbfs / 20)
        o = f(np.array([v]))[0]
        print(f"| {dbfs:+d} dBFS | {20*np.log10(o):+.2f} dBFS | {20*np.log10(o/v):+.3f} dB | {thd(f, v):.0f} dB |")


table(ceiling, "Safety ceiling")
print(f"\nAsymptote: 4.0 = {20*np.log10(4):+.2f} dBFS (approached, never reached). Not a 0 dBFS limiter.")
table(opamp, "Output-amp curve (PRE on, OUT ATT +4, GAIN 0 dB)")
print("\nAsymptote: 1.0 x OUT ATT x OUT GAIN (= 0 dBFS at +4 / 0 dB), then the safety ceiling.")

from engine import Engine, build
build()
sr = 48000
t = np.arange(sr // 2) / sr
print("\n| End-to-end (BALANCE 0, +4/+4) | input | output peak |\n|---|---|---|")
for pre in (1, 0):
    for gain in (0, 12):
        for dbfs in (0, 6, 12):
            x = 10 ** (dbfs / 20) * np.sin(2 * np.pi * 997 * t)
            y = Engine(sr, balance=0, pre_on=pre, out_gain=gain).run(x)[0][sr // 4:]
            print(f"| PRE {'on' if pre else 'off'}, GAIN {gain:+d} dB | {dbfs:+d} dBFS | {20*np.log10(np.abs(y).max()):+.2f} dBFS |")

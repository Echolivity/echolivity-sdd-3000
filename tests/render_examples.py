#!/usr/bin/env python3
"""Render audio examples of every major function through the tested engine."""
import json, os, sys
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(__file__))
from engine import Engine, ROOT, REF_SO, build

SR = 48000
OUT = os.path.join(ROOT, "audio_examples")
progs = json.load(open(os.path.join(ROOT, "presets", "factory_programs.json")))
rng = np.random.default_rng(11)


def pluck(f, dur, amp=0.3):
    n = int(SR * dur)
    L = int(SR / f)
    buf = rng.uniform(-1, 1, L)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % L]
        buf[i % L] = 0.996 * 0.5 * (buf[i % L] + buf[(i + 1) % L])
    return out * amp * np.exp(-np.arange(n) / (SR * 1.2))


def phrase(bpm=120, bars=2):
    beat = 60 / bpm
    notes = [(0, 220.0), (0.5, 261.6), (1, 329.6), (1.75, 392.0), (2.5, 329.6), (3, 293.7),
             (4, 220.0), (4.75, 246.9), (5.5, 196.0)]
    x = np.zeros(int(SR * beat * 4 * bars + SR * 0.1))
    for t, f in notes:
        s = int(t * beat * SR)
        p = pluck(f, 1.2)
        e = min(len(x), s + len(p))
        x[s:e] += p[:e - s]
    return x


def drums(bpm=120, bars=2):
    beat = 60 / bpm
    x = np.zeros(int(SR * beat * 4 * bars))
    t = np.arange(int(0.25 * SR)) / SR
    kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 14) * 0.5
    sn = rng.uniform(-1, 1, len(t)) * np.exp(-t * 25) * 0.25 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.15
    hat = rng.uniform(-1, 1, len(t)) * np.exp(-t * 90) * 0.08
    for b in range(4 * bars):
        s = int(b * beat * SR)
        k = kick if b % 2 == 0 else sn
        x[s:s + len(k)] += k[:len(x) - s]
        h = s + int(beat * SR / 2)
        if h < len(x):
            x[h:h + len(hat)] += hat[:len(x) - h]
    return x


def vocalish(dur=2.0):
    t = np.arange(int(SR * dur)) / SR
    f0 = 180 * (1 + 0.02 * np.sin(2 * np.pi * 5 * t))
    ph = np.cumsum(f0) / SR
    x = sum(np.sin(2 * np.pi * k * ph) / k for k in range(1, 12))
    env = np.minimum(1, t * 8) * np.minimum(1, (dur - t) * 6)
    return x * env * 0.12


def pad(x, secs):
    return np.concatenate([x, np.zeros(int(SR * secs))])


def prog(slot):
    v = dict(progs["programs"][slot - 1]["values"])
    return v


def render(name, x, xr=None, auto=None, so=None, sub="", **params):
    e = Engine(SR, so=so, tempo=120, **params)
    y = e.run(x, xr, automation=auto)
    st = np.stack([y[0], y[1]], 1)
    bad = int(np.sum(~np.isfinite(st)))
    st = np.nan_to_num(st, nan=0.0, posinf=0.0, neginf=0.0)   # WAV cannot store NaN/inf
    pk = np.max(np.abs(st))
    if pk > 0.99:
        st = st * 0.99 / pk
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    wavfile.write(os.path.join(OUT, sub, name + ".wav"), SR, (st * 32767).astype(np.int16))
    print(f"{name}: peak {20 * np.log10(pk + 1e-12):.1f} dBFS" + (f", {bad} non-finite samples written as 0" if bad else ""))


def main():
    os.makedirs(OUT, exist_ok=True)
    ph = phrase()
    dr = drums()
    mix = ph.copy()
    mix[:len(dr)] += dr * 0.6
    src = pad(mix, 0.0)
    wavfile.write(os.path.join(OUT, "00_dry_source.wav"), SR, (np.stack([src, src], 1) * 32767).astype(np.int16))
    render("01_classic_echo", pad(ph, 4), **prog(1))
    render("02_short_slap", pad(mix, 1.5), **prog(2))
    p3 = prog(3)
    s = len(dr)
    render("03_dub_regeneration_sync", pad(dr * 0.8, 10),
           auto=[(s + int(2 * SR), {"feedback": 7.6}), (s + int(6 * SR), {"feedback": 5.0})], **p3)
    render("04_metallic_flange", pad(np.tile(dr, 2), 2), **prog(4))
    render("05_wide_doubling_stereoA", pad(ph, 1.5), out_mode=1, **prog(5))
    render("06_vibrato", pad(vocalish(4.0), 0.5), **prog(6))
    render("07_random_drift", pad(ph, 4), **prog(7))
    # hold: play phrase, freeze, then play a different line on top
    h_src = pad(ph, 0)
    over = pad(vocalish(3.0), 6)
    x = np.concatenate([h_src, over])
    render("08_infinite_hold_then_play_over", x, auto=[(len(h_src) - int(0.05 * SR), {"hold": 1})], **prog(8))
    render("09_rhythmic_modulation_square", pad(ph, 4), **prog(9))
    render("10_filters_in_loop_LOW500_HIGH2k", pad(dr[:int(SR * 0.6)], 5), time_ms=300, feedback=6.2,
           lowcut=3, highcut=3, balance=6)
    render("11_regen_invert_flange_compare", pad(np.tile(dr, 2), 1),
           auto=[(len(dr), {"fb_inv": 1})], time_ms=6, feedback=5.5, intensity=4, frequency=2.5, balance=5)
    render("12_envelope_doppler", pad(ph, 3), waveform=3, intensity=6, time_ms=300, feedback=4, balance=5)
    render("13_preamp_crunch_minus10_delay_bypassed", pad(mix, 0.5), in_range=1, drive=6, bypass=1)
    q = vocalish(2.0) * 0.08
    render("14a_converter_13bit_quiet_tail", pad(q, 3), time_ms=200, feedback=6.5, balance=10, converter=0,
           out_gain=12)
    render("14b_converter_clean_quiet_tail", pad(q, 3), time_ms=200, feedback=6.5, balance=10, converter=1,
           out_gain=12)
    render("15_stereoB_plus_minus_mix", pad(ph, 2), out_mode=2, time_ms=180, feedback=4, balance=5)
    render("16_self_oscillation_bounded", pad(dr[:int(SR * 0.5)], 6), time_ms=50, feedback=10, lowcut=3,
           highcut=3, balance=10, loop_sat=1)
    render("17_time_change_glide", pad(np.tile(ph, 1), 3), auto=[(int(SR * 2), {"time_ms": 150}),
                                                                 (int(SR * 4), {"time_ms": 600})],
           time_ms=400, feedback=5, balance=5, time_glide=1, time_mode=1)


def chord(secs):
    """sustained chord (the material on which a HOLD-release click is most exposed)"""
    t = np.arange(int(SR * secs)) / SR
    x = sum(np.sin(2 * np.pi * f * t + k) for k, f in enumerate((196.0, 246.9, 293.7, 392.0))) * 0.05
    return x * np.minimum(1, t * 4)


def regression():
    """v1.0.1 vs v1.0.2 on identical input and settings (audio_examples/regression/).
    Sustained chord, effect only (BALANCE 10), as on a return track."""
    src = chord(10.0)
    for tag, so in (("v1.0.1", REF_SO), ("v1.0.2", None)):
        for T in (380, 1008):
            render(f"hold_release_T{T}_{tag}", src, so=so, sub="regression",
                   auto=[(int(SR * 2.5), {"hold": 1}), (int(SR * 5.0), {"hold": 0})],
                   time_ms=T, feedback=4, balance=10)
        render(f"hold_release_then_reengage_{tag}", src, so=so, sub="regression",
               auto=[(int(SR * 2.5), {"hold": 1}), (int(SR * 5.0), {"hold": 0}), (int(SR * 5.8), {"hold": 1})],
               time_ms=250, feedback=4, balance=10)
        ph = phrase()
        dr = drums()
        mix = ph.copy()
        mix[:len(dr)] += dr * 0.6
        x = np.concatenate([mix, mix, mix, mix])
        x[int(SR * 2.0):int(SR * 2.0) + 64] = np.nan          # e.g. a misbehaving upstream plug-in
        render(f"invalid_input_nan_at_2s_{tag}", x, so=so, sub="regression", time_ms=380, feedback=5, balance=5)


if __name__ == "__main__":
    build()          # v1.0.2: works from a clean checkout (build/ is not shipped)
    main()
    regression()

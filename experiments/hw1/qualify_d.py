#!/usr/bin/env python3
"""
HW-1 remediation: qualification measurements, production vs candidate D (C builds of the gen~ code).
Writes results/qualification_d.json and plots. Nothing in docs/, src/, tests/ is written.

  A  spurs: the four reported cases, sweeps 100 Hz-20 kHz at 44.1/48/88.2/96/192 kHz, both the memory
     path (TIME 20) and the TIME-0 path; conditions (FB 5, modulation, 13-bit, nominal level)
  B  effect-path response, tone-only (least-squares sine fit), 44.1/48/96 kHz, TIME 0 and TIME 20
  C  timing: TIME-0 latency, absolute and TIME-0-relative echo error 1..1023 ms, all rates;
     feedback period (cross-correlation of repeats); TIME 0 <-> 1 ms switching click
  D  memory-path group delay / dispersion (1, 5, 10, 17 kHz)
  E  corrected-method evidence for the tests classified as measurement defects
"""
import json, os, sys
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, HERE)
import engine  # noqa
from engine import Engine  # noqa
from reproduce import spurs, spectrum, NOM  # noqa
import run_tests as RT  # noqa

OUT = os.path.join(HERE, "results")
ENG = {"production": os.path.join(ROOT, "build", "engine.so"),
       "candidate_D": os.path.join(HERE, "build", "engine_d.so")}
SWEEP = [100, 200, 500, 1000, 2000, 3000, 5000, 7000, 8000, 10000, 12000, 14000, 15000, 16000, 17000, 18000, 19000, 20000]
RES = {}


def run(so, sr, x, xr=None, pre=0.1, auto=None, **p):
    e = Engine(sr, so=so, **p)
    e.silence(pre)
    return e.run(x, xr, automation=auto)


def sine(sr, f, secs, a):
    return a * np.sin(2 * np.pi * f * np.arange(int(secs * sr)) / sr)


def tone_gain_db(y, sr, f, a):
    t = np.arange(len(y)) / sr
    A = np.stack([np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t), np.ones_like(t)], 1)
    c = np.linalg.lstsq(A, y, rcond=None)[0]
    return 20 * np.log10(np.hypot(c[0], c[1]) / a)


def outside_energy_db(y, sr, f0, half=400):
    fr, S = spectrum(y, sr)
    P = S ** 2
    band = np.abs(fr - f0) < half
    return float(10 * np.log10(P[~band & (fr > 20)].sum() / P[band].sum()))


# ------------------------------------------------------------------------------------------- A
def part_a():
    a = NOM * 0.1
    cases = []
    for sr, f0 in ((48000, 17000), (48000, 15000), (44100, 1000), (44100, 17000)):
        row = dict(host=sr, tone=f0)
        for w, so in ENG.items():
            for T in (0, 20):
                y = run(so, sr, sine(sr, f0, 1.0, a), time_ms=T, feedback=0, balance=10, converter=1, pre_on=0)[0][sr // 2:]
                _, sp = spurs(y, sr, f0, n=2, floor_db=-200)
                row[f"{w}_T{T}"] = sp
        cases.append(row)
    sweep = {}
    for sr in (44100, 48000, 88200, 96000, 192000):
        for T in (0, 20):
            for w, so in ENG.items():
                worst = []
                for f0 in SWEEP:
                    y = run(so, sr, sine(sr, f0, 1.0, a), time_ms=T, feedback=0, balance=10, converter=1, pre_on=0)[0][sr // 2:]
                    _, sp = spurs(y, sr, f0, n=1, floor_db=-200)
                    worst.append(sp[0][1] if sp else -200.0)
                sweep[f"{sr}_T{T}_{w}"] = worst
        print("A sweep", sr, {k: max(v) for k, v in sweep.items() if k.startswith(str(sr))}, flush=True)
    cond = {}
    for name, p in (("FB 5, 50 ms", dict(time_ms=50, feedback=5)), ("modulation INT 2 TRI", dict(time_ms=200, intensity=2, frequency=3)),
                    ("13-bit, PRE on, -20 dB", dict(time_ms=20)), ("nominal level, defaults", dict(time_ms=20, _lvl=1.0))):
        for sr in (44100, 48000):
            for w, so in ENG.items():
                q = dict(p); lvl = q.pop("_lvl", 0.1)
                x = sine(sr, 17000, 3.0, NOM * lvl)
                y = run(so, sr, x, balance=10, **({"converter": 1, "pre_on": 0} if "13-bit" not in name and lvl < 1 else {}), **q)[0][sr:]
                cond[f"{name} @ {sr}: {w}"] = round(outside_energy_db(y, sr, 17000), 1)
    RES["A_spurs"] = dict(reported_cases=cases, sweep_worst_db=sweep, sweep_freqs=SWEEP,
                          conditions_energy_outside_tone_db=cond,
                          note="CLEAN converter, PRE off, -20 dB re nominal unless named; spur re wanted tone")


# ------------------------------------------------------------------------------------------- B
def part_b():
    out = {}
    f = [20, 50, 100, 200, 500, 1000, 2000, 4000, 6000, 8000, 10000, 12500, 14000, 15000, 16000, 17000, 18000, 19000, 20000]
    a = NOM * 0.1
    for sr in (44100, 48000, 96000):
        for T in (0, 20):
            for w, so in ENG.items():
                g = []
                for f0 in f:
                    y = run(so, sr, sine(sr, f0, 0.6, a), time_ms=T, feedback=0, balance=10, pre=0.05)[0][int(0.3 * sr):]
                    g.append(tone_gain_db(y, sr, f0, a))
                g = np.array(g) - g[f.index(1000)]
                out[f"{sr}_T{T}_{w}"] = [round(float(v), 2) for v in g]
    RES["B_response_tone_only"] = dict(freqs=f, db_re_1k=out, spec="SM: 20 Hz-17 kHz +0.5/-3 dB",
                                       note="defaults (13-bit, PRE on), -20 dB re nominal, least-squares tone fit")


# ------------------------------------------------------------------------------------------- C
def echo_ms(so, sr, T, **p):
    return RT.echo_delay_ms(Engine(sr, so=so), T, sr, **p)


def part_c():
    tim = {}
    for sr in (44100, 48000, 88200, 96000, 176400, 192000):
        for w, so in ENG.items():
            base = echo_ms(so, sr, 0)
            errs = {T: round((echo_ms(so, sr, T) - T) * 1000, 2) for T in (1, 2, 5, 10, 100, 333, 500, 1023)}
            tim[f"{sr}_{w}"] = dict(time0_latency_ms=round(base, 4), abs_error_us=errs,
                                    worst_rel_error_us=round(max(abs(v - base * 1000) for v in errs.values()), 2))
    # feedback period by cross-correlation of successive repeats, 50 ms, FB 5
    per = {}
    for sr in (44100, 48000, 96000):
        for w, so in ENG.items():
            x = np.zeros(int(0.6 * sr)); x[int(0.01 * sr)] = 0.3
            y = run(so, sr, x, time_ms=50, feedback=5, balance=10)[0]
            T = int(0.05 * sr); i0 = int(0.01 * sr)
            ps = []
            for k in range(1, 6):
                a_ = y[i0 + k * T - 200: i0 + k * T + 600]; b_ = y[i0 + (k + 1) * T - 200: i0 + (k + 1) * T + 600]
                c = signal.correlate(b_, a_, "full"); i = np.argmax(c)
                # parabolic refinement
                d = (c[i - 1] - c[i + 1]) / (2 * (c[i - 1] - 2 * c[i] + c[i + 1]))
                ps.append((T + i - (len(a_) - 1) + d) / sr * 1000)
            per[f"{sr}_{w}"] = [round(v, 4) for v in ps]
    # TIME 0 <-> 1 ms switching (short path <-> memory path) and 0 <-> 380: click metric as t_clicks
    sw = {}
    sr = 48000
    xx = RT.tone(sr, 220, 2.0, RT.NOM) + RT.tone(sr, 330, 2.0, RT.NOM * 0.5)
    for name, b, a in (("TIME 0->1", 0, 1), ("TIME 1->0", 1, 0), ("TIME 0->380", 0, 380), ("TIME 380->0", 380, 0)):
        for w, so in ENG.items():
            e = Engine(sr, so=so, time_ms=b, feedback=3, balance=5); e.run(xx)
            y = e.run(xx, automation=[(sr, dict(time_ms=a))])[0]
            e2 = Engine(sr, so=so, time_ms=b, feedback=3, balance=5); e2.run(xx); y2 = e2.run(xx)[0]
            hf_r = RT.hf(y, sr)[sr - 480: sr + int(0.06 * sr)].max()
            sw[f"{name}: {w}"] = dict(click_metric=round(RT.click_metric(y, sr, 1.0), 2),
                                      abs_hf_peak=float(hf_r), abs_3rd_diff_peak=float(np.abs(np.diff(y, 3))[sr - 480:sr + 2880].max()))
    RES["C_timing"] = dict(echo=tim, feedback_period_50ms_xcorr=per, path_switching=sw)


# ------------------------------------------------------------------------------------------- D
def part_d():
    gd = {}
    for sr in (44100, 48000, 96000):
        for w, so in ENG.items():
            x = np.zeros(int(0.3 * sr)); x[100] = NOM * 0.05
            y = run(so, sr, x, time_ms=20, feedback=0, balance=10, converter=1, pre_on=0, pre=0.05)[0]
            i0 = 100 + int(0.02 * sr)
            seg = y[i0 - 64: i0 + 4096 - 64]
            H = np.fft.rfft(seg); fr = np.fft.rfftfreq(len(seg), 1 / sr)
            ph = np.unwrap(np.angle(H)); g = -np.gradient(ph, 2 * np.pi * fr) * 1000 - 64 / sr * 1000
            gd[f"{sr}_{w}"] = {str(f): round(float(np.interp(f, fr, g)), 4) for f in (1000, 5000, 10000, 15000, 17000)}
    RES["D_group_delay_ms_re_TIME"] = gd


# ------------------------------------------------------------------------------------------- E
def part_e():
    ev = {}
    sr = 48000
    # E1 HIGH 8 kHz at 16 kHz, tone-only vs rms (t_filters_static method)
    for w, so in ENG.items():
        r = {}
        for meth in ("rms", "tone"):
            vals = {}
            for hc in (0, 1):
                x = RT.tone(sr, 16000, 0.8)
                y = run(so, sr, x, time_ms=20, feedback=0, balance=10, highcut=hc, lowcut=0, pre=0.15)[0][int(0.5 * sr):]
                xx = x[int(0.5 * sr):]
                vals[hc] = 20 * np.log10(RT.rms(y) / RT.rms(xx)) if meth == "rms" else tone_gain_db(y, sr, 16000, np.abs(xx).max())
            r[meth] = round(vals[1] - vals[0], 2)
        ev[f"HIGH 8k at 16 kHz: {w}"] = r
    # E2 effect response at 17 kHz, rms vs tone-only (t_wet_gain_and_response method)
    for w, so in ENG.items():
        x = RT.tone(sr, 17000, 0.6, RT.NOM * 0.1); x1 = RT.tone(sr, 1000, 0.6, RT.NOM * 0.1)
        y = run(so, sr, x, time_ms=20, feedback=0, balance=10, pre=0.0)[0][int(0.3 * sr):]
        y1 = run(so, sr, x1, time_ms=20, feedback=0, balance=10, pre=0.0)[0][int(0.3 * sr):]
        xx = x[int(0.3 * sr):]
        ev[f"17 kHz effect response: {w}"] = dict(rms=round(20 * np.log10(RT.rms(y) / RT.rms(xx)), 2),
                                                  tone=round(tone_gain_db(y, sr, 17000, np.abs(xx).max()) - tone_gain_db(y1, sr, 1000, np.abs(xx).max()), 2))
    # E3 click metric numerator/denominator (all t_clicks scenarios): absolute 3rd-difference peaks
    xx = RT.tone(sr, 220, 2.0, RT.NOM) + RT.tone(sr, 330, 2.0, RT.NOM * 0.5)
    for name, before, after in (("output INV", dict(balance=5), dict(out_inv=1)), ("HIGH FLAT->2k", dict(feedback=5), dict(highcut=3)),
                                ("delay time 380->120 ms (glide)", dict(time_ms=380, time_glide=1), dict(time_ms=120))):
        for w, so in ENG.items():
            base = dict(time_ms=380, feedback=3, balance=5); base.update(before)
            e = Engine(sr, so=so, **base); e.run(xx)
            y = e.run(xx, automation=[(sr, after)])[0]
            d = np.abs(np.diff(y, 3))
            ev[f"click '{name}': {w}"] = dict(transient_peak=float(d[sr - 480:sr + 2880].max()),
                                             steady_ref=float(max(d[int(0.3 * sr):sr - 2400].max(), d[sr + 12000:sr + 28800].max())),
                                             ratio=round(RT.click_metric(y, sr, 1.0), 2))
    # E4 non-finite input == its documented clamp value; delay sensitivity of the ENV/FB6 scenario
    p = dict(feedback=6, hold=0, waveform=3, intensity=8)
    for w, so in ENG.items():
        x1 = RT.tone(sr, 440, 1.5); x1[1000:2000] = np.tile([np.inf, -np.inf, np.nan, 0.1], 250)
        x2 = RT.tone(sr, 440, 1.5); x2[1000:2000] = np.tile([1000.0, -1000.0, 0.0, 0.1], 250)
        y1 = run(so, sr, x1, time_ms=200, balance=5, pre=0, **p); y2 = run(so, sr, x2, time_ms=200, balance=5, pre=0, **p)
        same = bool(np.max(np.abs(y1 - y2)) == 0)
        sens = {}
        for T in (198, 199, 200, 201, 202):
            ref = run(so, sr, RT.tone(sr, 440, 1.5), time_ms=T, balance=5, pre=0, **p)
            yy = run(so, sr, x1, time_ms=T, balance=5, pre=0, **p)
            sens[T] = round(RT.db(RT.rms(yy[0][-sr // 4:]) / RT.rms(ref[0][-sr // 4:])), 2)
        ev[f"NaN/inf burst: {w}"] = dict(bit_identical_to_finite_clamp_values=same, level_dev_db_vs_TIME=sens)
    # E5 FB 10 tail 'DC' statistic over seeds and delay times (t_feedback_extreme, last combination)
    for w, so in ENG.items():
        vals = []
        for seed in range(21, 27):
            for T in (36, 37, 38):
                rng = np.random.default_rng(seed)
                e = Engine(sr, so=so, time_ms=T, feedback=10, balance=10, in_range=0, in_level=10, out_mode=3,
                           waveform=2, intensity=10, frequency=8)
                x = np.concatenate([rng.uniform(-1, 1, sr * 4) + 0.5, np.zeros(sr * 8)])
                y = e.run(x, rng.uniform(-1, 1, len(x)))
                vals.append(max(abs(np.mean(y[0][-sr * 2:])), abs(np.mean(y[1][-sr * 2:]))))
        ev[f"FB10 tail mean (18 runs): {w}"] = dict(median=float(np.median(vals)), max=float(np.max(vals)),
                                                   n_over_0p003=int(np.sum(np.array(vals) > 0.003)))
    # E6 HOLD release at full nominal level: absolute >5 kHz peak in the switchover window
    for w, so in ENG.items():
        engine.SO = so
        R, K, N = RT.hold_release_case(48000, 120, 1, lvl=1.0)
        a_, b_ = int(48000 * 0.118), int(48000 * 0.135)
        ev[f"HOLD release switchover, full level: {w}"] = dict(
            released_hf_peak=float(RT.hf(R[0], 48000)[a_:b_].max()), kept_hf_peak=float(RT.hf(K[0], 48000)[a_:b_].max()),
            never_held_hf_peak=float(RT.hf(N[0], 48000)[a_:b_].max()), excess_db=round(RT.click_excess(R[0], (K[0], N[0]), 48000, a_, b_), 1))
    engine.SO = ENG["production"]
    # E7 EXT loop period by cross-correlation (t_loop_comp scenario)
    for w, so in ENG.items():
        lat, T = 512, 200
        for comp in (0.0, 1000 * lat / sr):
            e = Engine(sr, so=so, time_ms=T, balance=10, fb_route=1, loop_comp=comp, **{"return": 6}); e.silence(0.1)
            x = np.zeros(int(1.5 * sr)); x[0] = 0.5
            o = e.run(x, loop_latency=lat)[0]
            per = T + (1000 * lat / sr if comp == 0 else 0)
            segs = [o[int((k * per + T - 6) * sr / 1000): int((k * per + T + 8) * sr / 1000)] for k in range(0, 4)]
            pp = []
            for k in range(3):
                c = signal.correlate(segs[k + 1], segs[k], "full"); i = np.argmax(c) - (len(segs[k]) - 1)
                st = int(((k + 1) * per + T - 6) * sr / 1000) - int((k * per + T - 6) * sr / 1000)
                pp.append(round((st + i) / sr * 1000, 3))
            ev[f"EXT period LOOP COMP {comp:.2f}: {w}"] = pp
    # E8 FB ROUTE INT deaf to the return inputs (candidate against itself)
    for w, so in ENG.items():
        rng = np.random.default_rng(5)
        x = RT.tone(sr, 330, 2.0)
        a1 = run(so, sr, x, time_ms=120, feedback=10, intensity=3, frequency=4, lowcut=1, highcut=2, pre=0)
        e = Engine(sr, so=so, time_ms=120, feedback=10, intensity=3, frequency=4, lowcut=1, highcut=2)
        b1 = e.run(x, ret=np.stack([rng.uniform(-1, 1, len(x)), rng.uniform(-1, 1, len(x))]))
        ev[f"INT deaf to return: {w}"] = float(np.max(np.abs(a1[:2] - b1[:2])))
    # E9 gain-ranging staircase at identical absolute levels, TIME 0 and TIME 20
    for w, so in ENG.items():
        for T in (0, 20):
            row = []
            for rel in (-2, -4, -8, -10, -14, -20):
                aa = NOM * 10 ** ((5.0 + rel) / 20)
                x = sine(sr, 997, 1.5, aa)
                y13 = run(so, sr, x, time_ms=T, feedback=0, balance=10, pre_on=0)[0][sr // 2:]
                ycl = run(so, sr, x, time_ms=T, feedback=0, balance=10, pre_on=0, converter=1)[0][sr // 2:]
                row.append(round(float(RT.db(RT.rms(y13 - ycl) / RT.rms(ycl)) + rel), 1))
            ev[f"gain-ranging error re +9 dBm, T{T}: {w}"] = row
    RES["E_corrected_methods"] = ev


def plots():
    A = RES["A_spurs"]
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.3), sharey=True)
    for ax, sr in zip(axs, (44100, 48000, 96000)):
        for k, st in ((f"{sr}_T20_production", "o-"), (f"{sr}_T20_candidate_D", "s-"), (f"{sr}_T0_candidate_D", "^--")):
            ax.plot(A["sweep_freqs"], A["sweep_worst_db"][k], st, ms=3, label=k.split("_", 1)[1].replace("_", " "))
        ax.set_xscale("log"); ax.set_title(f"host {sr / 1000:g} kHz"); ax.grid(alpha=0.3); ax.set_xlabel("tone (Hz)")
    axs[0].set_ylabel("worst in-band spur re tone (dB)"); axs[0].legend(fontsize=8)
    fig.suptitle("HW-1: worst conversion spur, production vs candidate D (full device, C build)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "d_spurs_full_device.png"), dpi=110)
    B = RES["B_response_tone_only"]
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.3), sharey=True)
    for ax, sr in zip(axs, (44100, 48000, 96000)):
        for k, st in ((f"{sr}_T20_production", "o-"), (f"{sr}_T20_candidate_D", "s-"), (f"{sr}_T0_candidate_D", "^--")):
            ax.plot(B["freqs"], B["db_re_1k"][k], st, ms=3, label=k.split("_", 1)[1].replace("_", " "))
        ax.axhspan(-3, 0.5, xmin=0, xmax=1, color="g", alpha=0.06)
        ax.set_xscale("log"); ax.set_ylim(-8, 1.5); ax.set_title(f"host {sr / 1000:g} kHz"); ax.grid(alpha=0.3)
    axs[0].set_ylabel("effect path re 1 kHz (dB), tone-only"); axs[0].legend(fontsize=8)
    fig.suptitle("Effect-path response (green: SM +0.5/-3 dB band)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "d_response_full_device.png"), dpi=110)


def main():
    if len(sys.argv) > 1:
        ENG["candidate_D"] = os.path.abspath(sys.argv[1])
    for part in (part_a, part_b, part_c, part_d, part_e):
        part()
        json.dump(RES, open(os.path.join(OUT, "qualification_d.json"), "w"), indent=1, default=str)
        print("done", part.__name__, flush=True)
    plots()


if __name__ == "__main__":
    main()

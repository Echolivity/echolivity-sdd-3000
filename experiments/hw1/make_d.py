#!/usr/bin/env python3
"""
HW-1 remediation: EXPERIMENTAL full-device variant with candidate D
("continuous-time analog-prototype conversion" + "TIME-0 error-feedforward path").

Reads the PRODUCTION GenExpr (src/gen/echolivity_core.genexpr, untouched) and writes a patched
copy to experiments/hw1/build/echolivity_core_d.genexpr. Only the host <-> memory-clock
conversion changes:

  host -> tick : linear interpolation ->  x(t_k) = sum_n x[n] h_in(t_k - n), h_in a fixed
                 analog low-pass (7th-order elliptic 21 kHz + real poles at 50/70 kHz),
                 evaluated exactly at each tick instant from a host-rate one-pole state per
                 pole: x(t_k) = sum_i Re(s_i[n-1] exp(p_i tau)). No kernel table, no look-ahead.
  tick -> host : ZOH integrated over the host period -> the authentic ZOH staircase filtered by
                 the same analog low-pass in continuous time and sampled at the host instants:
                 y(n) = q(n) + sum_i Re(z_i(n)), z_i += dq_k (r_i/p_i) exp(p_i (n - t_k)).
  latency      : the analog pair adds ~0.09 ms of group delay. TIME >= 1 ms: an integer number
                 of memory ticks is subtracted from the read offset so the echo lands where it
                 did in production (residual < 1/2 tick). TIME 0 (and continuous TIME below
                 the compensation): "error feedforward" short path - the wet signal is the
                 converter input through a matching host-rate biquad M plus the converter's
                 own error (quantisation, gain ranging, clipping) reconstructed through the
                 analog output filter. Same response, same converter character, no images,
                 and production's TIME-0 latency. Crossfaded (10 ms) with the memory path.
  HF voicing   : the droop-EQ table is refitted (fit_d.py) so the effect path matches the
                 production effect path (not a flatter one).

Everything else (quantiser, gain ranging, emphasis, AA/reconstruction filters, feedback, HOLD,
modulation, routing, outputs) is the production code.

Usage: python3 experiments/hw1/make_d.py [--cal path/to/d_calibration.json] [--no-short]
"""
import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "src", "gen", "echolivity_core.genexpr")
OUT = os.path.join(HERE, "build", "echolivity_core_d.genexpr")
CAL = os.path.join(HERE, "d_calibration.json")
sys.path.insert(0, HERE)
import convmodel as C  # noqa

PROTO = dict(order=7, rp=0.05, rs=90.0, fp_hz=21000.0, extra_poles_hz=(50000.0, 70000.0))
RATES = (44100, 48000, 88200, 96000, 176400, 192000)


def poles():
    p, r, w = C.analog_proto(**PROTO)
    out = []
    for pi, ri, wi in zip(p, r, w):
        out.append(dict(pr=float(pi.real), pi=float(pi.imag) if wi == 2 else 0.0,
                        rr=float(ri.real), ri=float(ri.imag) if wi == 2 else 0.0, pair=bool(wi == 2)))
    return out


def f(v):
    return f"{v:.17g}"


def patch(text, cal, short=True):
    P = poles()

    def rep(a, b, cnt=1):
        nonlocal text
        assert text.count(a) == cnt, (a[:80], text.count(a))
        text = text.replace(a, b)

    CH = "lr"
    # ---------------------------------------------------------------- declarations
    hist = []
    for j, p in enumerate(P):
        for nm in ("e1r", "e1i", "rsr", "rsi", "cr", "ci", "ar", "ai"):
            hist.append(f"h_d{j}{nm}")
        for c in CH:
            for nm in ("sr", "si", "zr", "zi"):
                hist.append(f"h_dq{j}{c}{nm}")
    hist += ["h_eh_l", "h_eh_r",
             "h_dv_l", "h_dv_r", "h_sp", "h_mb0", "h_mb1", "h_mb2", "h_ma1", "h_ma2",
             "h_mz1_l", "h_mz2_l", "h_mz1_r", "h_mz2_r", "h_dcmp",
             "h_e2b0", "h_e2b1", "h_e2b2", "h_e2a1", "h_e2a2", "h_e2z1_l", "h_e2z2_l", "h_e2z1_r", "h_e2z2_r"]
    rep("History h_ph(0);", "History h_ph(0);\n" + "\n".join(f"History {h}(0);" for h in hist) +
        "   // HW-1 D: analog-prototype conversion state")

    # ---------------------------------------------------------------- coefficients (sr change)
    loads = []
    for j in range(len(P)):
        for nm in ("e1r", "e1i", "rsr", "rsi", "cr", "ci", "ar", "ai"):
            loads.append(f"d{j}{nm} = h_d{j}{nm};")
    loads += ["mb0 = h_mb0; mb1 = h_mb1; mb2 = h_mb2; ma1 = h_ma1; ma2 = h_ma2; dcmp = h_dcmp;",
              "e2b0 = h_e2b0; e2b1 = h_e2b1; e2b2 = h_e2b2; e2a1 = h_e2a1; e2a2 = h_e2a2;",
              "dmg = 0; dden = 0; e2_f0 = 0; e2_g = 0; e2_q = 0; e2_a = 0; e2_w = 0; e2_al = 0; e2_n = 0;"]
    calc = []
    for j, p in enumerate(P):
        calc.append(f"    d{j}ar = {f(p['pr'])} / sr;")
        calc.append(f"    d{j}ai = {f(p['pi'])} / sr;")
        calc.append(f"    dmg = exp(d{j}ar);")
        calc.append(f"    d{j}e1r = dmg * cos(d{j}ai);")
        calc.append(f"    d{j}e1i = dmg * sin(d{j}ai);")
        calc.append(f"    d{j}rsr = {f(p['rr'])} / sr;")
        calc.append(f"    d{j}rsi = {f(p['ri'])} / sr;")
        # c = r / p (dimensionless)
        den = p["pr"] ** 2 + p["pi"] ** 2
        cr = (p["rr"] * p["pr"] + p["ri"] * p["pi"]) / den
        ci = (p["ri"] * p["pr"] - p["rr"] * p["pi"]) / den
        calc.append(f"    d{j}cr = {f(cr)};")
        calc.append(f"    d{j}ci = {f(ci)};")
    # matching biquad M and latency compensation, per host rate (calibrated offline)
    calc.append("    mb0 = 1; mb1 = 0; mb2 = 0; ma1 = 0; ma2 = 0;")
    calc.append(f"    dcmp = {f(cal.get('default_cmp_ticks', 0))};")
    BOUNDS = {44100: None, 48000: 46050.0, 88200: 68100.0, 96000: 92100.0, 176400: 136200.0, 192000: 184200.0}
    UPPER = {44100: 46050.0, 48000: 68100.0, 88200: 92100.0, 96000: 136200.0, 176400: 184200.0, 192000: None}
    calc.append("    e2_f0 = 15000; e2_g = 0; e2_q = 0.7;   // identity unless calibrated")
    first = True
    for sr in RATES:
        k = str(sr)
        if k not in cal.get("rates", {}):
            continue
        c = cal["rates"][k]
        cond = f"sr < {UPPER[sr]}" if UPPER[sr] else "sr > 0"
        kw = "if" if first else "else if"
        first = False
        m = c.get("m", [1, 0, 0, 0, 0])
        calc.append(f"    {kw} ({cond}) {{")
        calc.append(f"        mb0 = {f(m[0])}; mb1 = {f(m[1])}; mb2 = {f(m[2])}; ma1 = {f(m[3])}; ma2 = {f(m[4])};")
        calc.append(f"        dcmp = {f(c.get('cmp_ticks', 0))};")
        e = cal.get("eq", {}).get(k)
        if e and len(e) == 6:
            calc.append(f"        e2_f0 = {e[3]:.3f}; e2_g = {e[4]:.4f}; e2_q = {e[5]:.4f};")
        calc.append("    }")
    calc += [
        "    // second RBJ peaking section (HW-1 D voicing match)",
        "    e2_a = pow(10, e2_g * 0.025);",
        "    e2_w = 2 * pi * min(e2_f0, 0.49 * sr) / sr;",
        "    e2_al = sin(e2_w) / (2 * e2_q);",
        "    e2_n = 1 / (1 + e2_al / e2_a);",
        "    e2b0 = (1 + e2_al * e2_a) * e2_n;",
        "    e2b1 = -2 * cos(e2_w) * e2_n;",
        "    e2b2 = (1 - e2_al * e2_a) * e2_n;",
        "    e2a1 = e2b1;",
        "    e2a2 = (1 - e2_al / e2_a) * e2_n;",
    ]
    rep("if (sr != h_sr) {\n", "\n".join(loads) + "\nif (sr != h_sr) {\n" + "\n".join(calc) + "\n")

    # refitted droop-EQ table (keeps the production response)
    if cal.get("eq"):
        import re
        for sr in RATES:
            e = cal["eq"].get(str(sr))
            if not e:
                continue
            old = {r[0]: r for r in json.load(open(os.path.join(ROOT, "tools", "hfcomp_table.json")))["rates"]}[sr]
            pat = re.compile(r"hf_fa = 23941\.000; hf_f0 = %.3f; hf_gdb = %.4f; hf_q = %.4f;" % (old[2], old[3], old[4]))
            mm = pat.search(text)
            assert mm, f"eq row {sr}"
            text = text[:mm.start()] + \
                f"hf_fa = 23941.000; hf_f0 = {e[0]:.3f}; hf_gdb = {e[1]:.4f}; hf_q = {e[2]:.4f};   // HW-1 D refit (section 1)" + \
                text[mm.end():]

    # ---------------------------------------------------------------- latency compensation
    rep("n_tgt = fixnan(clamp(ms * 64, 0, 65472));",
        "n_tgt = fixnan(clamp(ms * 64 - dcmp, 0, 65472));   // HW-1 D: minus the analog-pair latency (integer ticks)")

    # ---------------------------------------------------------------- per-sample setup
    setup = ["// HW-1 D: conversion states (z advanced to this host instant)"]
    for j, p in enumerate(P):
        for c in CH:
            setup.append(f"dq{j}{c}sr = h_dq{j}{c}sr; dq{j}{c}si = h_dq{j}{c}si;")
            if p["pair"]:
                setup.append(f"dq{j}{c}zr = d{j}e1r * h_dq{j}{c}zr - d{j}e1i * h_dq{j}{c}zi;")
                setup.append(f"dq{j}{c}zi = d{j}e1r * h_dq{j}{c}zi + d{j}e1i * h_dq{j}{c}zr;")
            else:
                setup.append(f"dq{j}{c}zr = d{j}e1r * h_dq{j}{c}zr; dq{j}{c}zi = 0;")
        setup.append(f"dx{j} = 0; dc{j} = 0; ds{j} = 0; dfr{j} = 0; dfi{j} = 0; dgr{j} = 0; dgi{j} = 0;")
    setup.append("dv_l = h_dv_l; dv_r = h_dv_r;")
    setup.append("xr_l = 0; xr_r = 0; vv_l = 0; vv_r = 0; dlt_l = 0; dlt_r = 0;")
    setup.append("xl_l = 0; xl_r = 0; ql_l = 0; ql_r = 0; el_l = 0; el_r = 0; ea_l = 0; ea_r = 0;")
    setup.append("eh_l = h_eh_l; eh_r = h_eh_r; q13s_l = 0; q13s_r = 0;")
    setup.append("xin_l = clamp(fixnan(xc_l), -16, 16); xin_r = clamp(fixnan(xc_r), -16, 16);")
    # short path selector
    setup += [
        "sp = h_sp; sp_t = 0; spc = na;",
        "if (p_time_glide > 0.5) {",
        "    if (ns < 0.5 && n_tgt < 0.5) {",
        "        sp_t = 1;",
        "    }",
        "}",
        "else {",
        "    if (xdir > 0.5) {",
        "        spc = nb;",
        "    }",
        "    if (abs(xf - xdir) < 0.0000001 && spc < 0.5 && n_tgt < 0.5) {",
        "        sp_t = 1;",
        "    }",
        "}",
        "if (hst > 0.5 || s_hm > 0) {",
        "    sp_t = 0;     // HOLD plays the memory: memory path only",
        "}",
    ]
    if not short:
        setup.append("sp_t = 0;")
    setup += [
        "if (h_init < 0.5) {",
        "    sp = sp_t;",
        "}",
        "sp = sp + clamp(sp_t - sp, -inv_sr / 0.010, inv_sr / 0.010);",
        "spw = sp * sp * (3 - 2 * sp);",
        # M biquad (TDF-II) on the converter input, host rate
        "mz1_l = h_mz1_l; mz2_l = h_mz2_l; mz1_r = h_mz1_r; mz2_r = h_mz2_r;",
        "my_l = mb0 * xin_l + mz1_l;",
        "mz1_l = fixdenorm(mb1 * xin_l - ma1 * my_l + mz2_l);",
        "mz2_l = fixdenorm(mb2 * xin_l - ma2 * my_l);",
        "my_r = mb0 * xin_r + mz1_r;",
        "mz1_r = fixdenorm(mb1 * xin_r - ma1 * my_r + mz2_r);",
        "mz2_r = fixdenorm(mb2 * xin_r - ma2 * my_r);",
    ]
    rep("acc_l = 0; acc_r = 0;\n", "acc_l = 0; acc_r = 0;\n" + "\n".join(setup) + "\n")

    # ---------------------------------------------------------------- tick loop
    rep("    acc_l = acc_l + dac_l * (tt - tl);\n    acc_r = acc_r + dac_r * (tt - tl);\n", "")
    ev = ["    // HW-1 D: per-tick exponentials, shared by both channels and both directions"]
    for j, p in enumerate(P):
        ev.append(f"    dx{j} = exp(d{j}ar * tt);")
        if p["pair"]:
            ev.append(f"    dc{j} = cos(d{j}ai * tt);")
            ev.append(f"    ds{j} = sin(d{j}ai * tt);")
            ev.append(f"    dfr{j} = (d{j}e1r * dc{j} + d{j}e1i * ds{j}) / dx{j};")
            ev.append(f"    dfi{j} = (d{j}e1i * dc{j} - d{j}e1r * ds{j}) / dx{j};")
            ev.append(f"    dgr{j} = d{j}cr * dfr{j} - d{j}ci * dfi{j};")
            ev.append(f"    dgi{j} = d{j}cr * dfi{j} + d{j}ci * dfr{j};")
        else:
            ev.append(f"    dgr{j} = d{j}cr * d{j}e1r / dx{j};")
    for c in CH:
        terms = []
        for j, p in enumerate(P):
            if p["pair"]:
                terms.append(f"2 * dx{j} * (dq{j}{c}sr * dc{j} - dq{j}{c}si * ds{j})")
            else:
                terms.append(f"dx{j} * dq{j}{c}sr")
        ev.append(f"    xr_{c} = " + " + ".join(terms) + ";")
    rep("    xi_l = clamp(xp_l + (xc_l - xp_l) * tt, -1, 0.999755859);   // converter full scale",
        "\n".join(ev) + "\n    xi_l = clamp(xr_l, -1, 0.999755859);   // converter full scale (HW-1 D: analog-filtered input at the tick)")
    rep("    xi_r = clamp(xp_r + (xc_r - xp_r) * tt, -1, 0.999755859);   // converter full scale",
        "    xi_r = clamp(xr_r, -1, 0.999755859);   // converter full scale (HW-1 D)")
    # TIME-0 short path: the converter's own error (quantisation, gain ranging, clipping) on a
    # host-aligned (linearly interpolated) copy of the input, held and box-integrated like production,
    # so it stays time-aligned with the direct signal M(x) and overload compresses exactly as the
    # memory path does. Only the error (<= -72 dB re signal below overload) goes through this cheap
    # reconstruction; the signal itself never does.
    sq = []
    for c in CH:
        sq += [f"    ea_{c} = ea_{c} + eh_{c} * (tt - tl);",
               f"    xl_{c} = xp_{c} + (xc_{c} - xp_{c}) * tt;",
               f"    ql_{c} = clamp(xl_{c}, -1, 0.999755859);",
               f"    if (abs(ql_{c}) < 0.5) {{",
               f"        q13s_{c} = floor(ql_{c} * 4096 + 0.5) * 0.000244140625;",
               "    }",
               "    else {",
               f"        q13s_{c} = floor(ql_{c} * 2048 + 0.5) * 0.00048828125;",
               "    }",
               f"    el_{c} = fixnan(ql_{c} + (q13s_{c} - ql_{c}) * lsb_q - xl_{c});",
               f"    eh_{c} = el_{c};"]
    rep("    q_l = fixnan(q_l);\n    q_r = fixnan(q_r);\n",
        "    q_l = fixnan(q_l);\n    q_r = fixnan(q_r);\n" + "\n".join(sq) + "\n")
    out = ["    // HW-1 D: staircase step -> analog output filter state"]
    for c in CH:
        out.append(f"    vv_{c} = w{c} * (1 - spw);")
        out.append(f"    dlt_{c} = vv_{c} - dv_{c};")
        out.append(f"    dv_{c} = vv_{c};")
        for j, p in enumerate(P):
            if p["pair"]:
                out.append(f"    dq{j}{c}zr = dq{j}{c}zr + dlt_{c} * dgr{j};")
                out.append(f"    dq{j}{c}zi = dq{j}{c}zi + dlt_{c} * dgi{j};")
            else:
                out.append(f"    dq{j}{c}zr = dq{j}{c}zr + dlt_{c} * dgr{j};")
    rep("    dac_l = wl;\n    dac_r = wr;\n", "    dac_l = wl;\n    dac_r = wr;\n" + "\n".join(out) + "\n")

    # ---------------------------------------------------------------- host output + input states
    fin = ["// HW-1 D: output = staircase + analog-filter correction (+ TIME-0 short path)"]
    for c in CH:
        terms = []
        for j, p in enumerate(P):
            terms.append(f"2 * dq{j}{c}zr" if p["pair"] else f"dq{j}{c}zr")
        fin.append(f"ea_{c} = ea_{c} + eh_{c} * (1 - tl);")
        fin.append(f"acc_{c} = dv_{c} + " + " + ".join(terms) + f" + spw * (my_{c} + ea_{c});")
    for j, p in enumerate(P):
        for c in CH:
            if p["pair"]:
                fin.append(f"dtmp = d{j}e1r * dq{j}{c}sr - d{j}e1i * dq{j}{c}si + d{j}rsr * xin_{c};")
                fin.append(f"dq{j}{c}si = fixdenorm(d{j}e1r * dq{j}{c}si + d{j}e1i * dq{j}{c}sr + d{j}rsi * xin_{c});")
                fin.append(f"dq{j}{c}sr = fixdenorm(dtmp);")
            else:
                fin.append(f"dq{j}{c}sr = fixdenorm(d{j}e1r * dq{j}{c}sr + d{j}rsr * xin_{c});")
    rep("acc_l = acc_l + dac_l * (1 - tl);\nacc_r = acc_r + dac_r * (1 - tl);\n",
        "dtmp = 0;\n" + "\n".join(fin) + "\n")

    for c in CH:
        rep(f"uq_{c} = u2_{c} + (eqy_{c} - u2_{c}) * p_hf_comp;\n",
            f"uq_{c} = u2_{c} + (eqy_{c} - u2_{c}) * p_hf_comp;\n"
            f"e2z1_{c} = h_e2z1_{c}; e2z2_{c} = h_e2z2_{c};   // HW-1 D: voicing section 2\n"
            f"e2y_{c} = e2b0 * uq_{c} + e2z1_{c};\n"
            f"e2z1_{c} = fixdenorm(e2b1 * uq_{c} - e2a1 * e2y_{c} + e2z2_{c});\n"
            f"e2z2_{c} = fixdenorm(e2b2 * uq_{c} - e2a2 * e2y_{c});\n"
            f"uq_{c} = uq_{c} + (e2y_{c} - uq_{c}) * p_hf_comp;\n")

    # ---------------------------------------------------------------- store
    st = []
    for j, p in enumerate(P):
        for nm in ("e1r", "e1i", "rsr", "rsi", "cr", "ci", "ar", "ai"):
            st.append(f"h_d{j}{nm} = d{j}{nm};")
        for c in CH:
            for nm in ("sr", "si", "zr", "zi"):
                st.append(f"h_dq{j}{c}{nm} = fixnan(fixdenorm(dq{j}{c}{nm}));")
    st += ["h_dv_l = fixnan(dv_l); h_dv_r = fixnan(dv_r); h_sp = fixnan(sp);",
           "h_eh_l = fixnan(eh_l); h_eh_r = fixnan(eh_r);",
           "h_mb0 = mb0; h_mb1 = mb1; h_mb2 = mb2; h_ma1 = ma1; h_ma2 = ma2; h_dcmp = dcmp;",
           "h_e2b0 = e2b0; h_e2b1 = e2b1; h_e2b2 = e2b2; h_e2a1 = e2a1; h_e2a2 = e2a2;",
           "h_e2z1_l = fixnan(e2z1_l); h_e2z2_l = fixnan(e2z2_l); h_e2z1_r = fixnan(e2z1_r); h_e2z2_r = fixnan(e2z2_r);",
           "h_mz1_l = fixnan(mz1_l); h_mz2_l = fixnan(mz2_l); h_mz1_r = fixnan(mz1_r); h_mz2_r = fixnan(mz2_r);"]
    rep("h_xp_l = fixnan(xc_l);", "h_xp_l = fixnan(xc_l);\n" + "\n".join(st))
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cal", default=CAL)
    ap.add_argument("--no-short", action="store_true")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    cal = json.load(open(a.cal)) if os.path.exists(a.cal) else {}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    t = patch(open(SRC).read(), cal, short=not a.no_short)
    open(a.out, "w").write(t)
    print(f"wrote {a.out} ({t.count(chr(10))} lines; cal={'yes' if cal else 'none'}, short={'off' if a.no_short else 'on'})")


if __name__ == "__main__":
    main()

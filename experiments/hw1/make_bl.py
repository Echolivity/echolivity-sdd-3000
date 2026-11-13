#!/usr/bin/env python3
"""
HW-1 investigation, step 6: EXPERIMENTAL full-device variant with candidate B
(band-limited, continuous-time kernel resampling in both clock-domain directions).

Reads the PRODUCTION GenExpr (src/gen/echolivity_core.genexpr, untouched) and writes a patched
copy to experiments/hw1/build/echolivity_core_bl.genexpr. Nothing in src/, dist/ or tools/ is
modified. Only the conversion between the host rate and the memory clock changes:

  host -> tick : linear interpolation          ->  windowed-sinc kernel in host time, L taps
  tick -> host : ZOH integrated over the period ->  each tick weighted by its hold time and
                                                    a windowed-sinc kernel in host time, L taps
  latency      : 0                              ->  L host samples, subtracted from the read
                                                    offset so TIME stays exact (TIME >= L/sr)

Everything else (quantiser, gain ranging, emphasis, AA/reconstruction filters, feedback, HOLD,
modulation, outputs) is the production code. Usage:
  python3 experiments/hw1/make_bl.py [--kernel-ms 0.5] [--fc 20000]
"""
import argparse, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "src", "gen", "echolivity_core.genexpr")
OUT = os.path.join(HERE, "build", "echolivity_core_bl.genexpr")


def patch(text, kernel_ms, fc):
    def rep(a, b, cnt=1):
        nonlocal text
        assert text.count(a) == cnt, (a[:70], text.count(a))
        text = text.replace(a, b)

    # declarations
    rep("Data mem(65536, 2);", "Data mem(65536, 2);\n"
        "Data hin(128, 2);      // HW-1 exp: host-rate input history\n"
        "Data tkr(256, 4);      // HW-1 exp: recent ticks (time, value L, value R, hold)\n"
        "Data kern(16385, 1);   // HW-1 exp: windowed-sinc kernel table")
    rep("History h_ph(0);", "History h_ph(0);\nHistory h_hc(0);\nHistory h_tw(0);\nHistory h_kl(0);")
    # kernel table, rebuilt on sample-rate change (depth-0 locals first)
    rep("if (sr != h_sr) {\n",
        "kl = h_kl; kd = 0; ki = 0; ku = 0; kz = 0; kwin = 0; kn = 0;\n"
        "if (sr != h_sr) {\n"
        f"    kl = 2 * max(4, floor({kernel_ms / 2:.6f} * 0.001 * sr + 0.5));   // HW-1 exp: kernel length (host samples)\n"
        "    kn = kl * 128;\n"
        "    ki = 0;\n"
        "    while (ki <= kn) {\n"
        "        ku = ki / 128 - kl * 0.5;\n"
        "        kz = ki / kn;\n"
        "        kwin = 0.35875 - 0.48829 * cos(2 * pi * kz) + 0.14128 * cos(4 * pi * kz) - 0.01168 * cos(6 * pi * kz);\n"
        f"        if (abs(ku) < 0.0000001) {{\n"
        f"            poke(kern, 2 * {fc:.1f} / sr * kwin, ki, 0);\n"
        "        }\n"
        "        else {\n"
        f"            poke(kern, sin(2 * pi * {fc:.1f} / sr * ku) / (pi * ku) * kwin, ki, 0);\n"
        "        }\n"
        "        ki = ki + 1;\n"
        "    }\n")
    # the droop EQ compensated the linear-interpolation / ZOH-box roll-off, which no longer exists
    m = re.search(r"Param p_hf_comp\(1", text)
    assert m, "p_hf_comp default"
    text = text.replace(m.group(0), "Param p_hf_comp(0", 1)
    # latency compensation: the conversion now delays by kl host samples
    rep("n_tgt = fixnan(clamp(ms * 64, 0, 65472));",
        "n_tgt = fixnan(clamp(ms * 64 - kl * 64000 / sr, 0, 65472));   // HW-1 exp: minus conversion latency")
    # input history + tick-time bookkeeping before the tick loop
    rep("acc_l = 0; acc_r = 0;\n",
        "acc_l = 0; acc_r = 0;\n"
        "hc = h_hc + 1;\n"
        "tw = h_tw;\n"
        "kd = kl * 0.5;\n"
        "poke(hin, xc_l, hc - floor(hc / 128) * 128, 0);\n"
        "poke(hin, xc_r, hc - floor(hc / 128) * 128, 1);\n"
        "bj = 0; bu = 0; bp = 0; bi = 0; bf = 0; bw = 0; bs = 0; bl_l = 0; bl_r = 0; bidx = 0; te = 0;\n"
        "ok_n = 0; tk = 0; tkt = 0; ow = 0; os_ = 0; oy_l = 0; oy_r = 0;\n")
    # input: band-limited evaluation at the tick instant (kd samples in the past)
    for c in "lr":
        rep(f"    xi_{c} = clamp(xp_{c} + (xc_{c} - xp_{c}) * tt, -1, 0.999755859);   // converter full scale",
            ("    te = tt - 1 - kd;\n"
             "    bl_l = 0; bl_r = 0; bs = 0;\n"
             "    bj = 0;\n"
             "    while (bj <= kl) {\n"
             "        bu = te + bj;\n"
             "        bp = (bu + kd) * 128;\n"
             "        if (bp >= 0 && bp < kl * 128) {\n"
             "            bi = floor(bp);\n"
             "            bf = bp - bi;\n"
             "            bw = peek(kern, bi, 0) * (1 - bf) + peek(kern, bi + 1, 0) * bf;\n"
             "            bidx = hc - bj + 128000;\n"
             "            bidx = bidx - floor(bidx / 128) * 128;\n"
             "            bl_l = bl_l + bw * peek(hin, bidx, 0);\n"
             "            bl_r = bl_r + bw * peek(hin, bidx, 1);\n"
             "            bs = bs + bw;\n"
             "        }\n"
             "        bj = bj + 1;\n"
             "    }\n"
             "    bs = max(bs, 0.000001);\n"
             if c == "l" else "") +
            f"    xi_{c} = clamp(bl_{c} / bs, -1, 0.999755859);   // converter full scale (HW-1 exp: band-limited input)")
    # output: store each tick (time, value, hold) instead of the ZOH accumulation
    rep("    dac_l = wl;\n    dac_r = wr;\n",
        "    dac_l = wl;\n    dac_r = wr;\n"
        "    poke(tkr, hc - 1 + tt, tw, 0);\n"
        "    poke(tkr, wl, tw, 1);\n"
        "    poke(tkr, wr, tw, 2);\n"
        "    poke(tkr, tdt, tw, 3);\n"
        "    tw = tw + 1;\n"
        "    if (tw >= 256) {\n"
        "        tw = tw - 256;\n"
        "    }\n")
    rep("acc_l = acc_l + dac_l * (1 - tl);\nacc_r = acc_r + dac_r * (1 - tl);\n",
        "// HW-1 exp: y = sum_k q_k * hold_k * h((hc - kd) - t_k), normalised\n"
        "oy_l = 0; oy_r = 0; os_ = 0; ok_n = 0; tk = tw + 255;\n"
        "if (tk >= 256) {\n"
        "    tk = tk - 256;\n"
        "}\n"
        "while (ok_n < 255) {\n"
        "    tkt = (hc - kd) - peek(tkr, tk, 0);\n"
        "    if (tkt >= kd || peek(tkr, tk, 3) <= 0) {      // older than the kernel, or never written (start-up)\n"
        "        ok_n = 999;\n"
        "    }\n"
        "    else {\n"
        "        bp = (tkt + kd) * 128;\n"
        "        if (bp >= 0 && bp < kl * 128) {\n"
        "            bi = floor(bp);\n"
        "            bf = bp - bi;\n"
        "            ow = (peek(kern, bi, 0) * (1 - bf) + peek(kern, bi + 1, 0) * bf) * peek(tkr, tk, 3);\n"
        "            oy_l = oy_l + ow * peek(tkr, tk, 1);\n"
        "            oy_r = oy_r + ow * peek(tkr, tk, 2);\n"
        "            os_ = os_ + ow;\n"
        "        }\n"
        "        tk = tk + 255;\n"
        "        if (tk >= 256) {\n"
        "            tk = tk - 256;\n"
        "        }\n"
        "        ok_n = ok_n + 1;\n"
        "    }\n"
        "}\n"
        "if (os_ < 0.5) {\n"
        "    os_ = 1;          // start-up: the kernel isn't filled yet; don't amplify a partial sum\n"
        "}\n"
        "acc_l = oy_l / os_;\n"
        "acc_r = oy_r / os_;\n")
    rep("h_xp_l = fixnan(xc_l);", "h_xp_l = fixnan(xc_l);\nh_hc = hc;\nh_tw = tw;\nh_kl = kl;")
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel-ms", type=float, default=0.5)
    ap.add_argument("--fc", type=float, default=20000.0)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    t = patch(open(SRC).read(), a.kernel_ms, a.fc)
    open(a.out, "w").write(t)
    print(f"wrote {a.out} ({t.count(chr(10))} lines; kernel {a.kernel_ms} ms, fc {a.fc:.0f} Hz)")


if __name__ == "__main__":
    main()

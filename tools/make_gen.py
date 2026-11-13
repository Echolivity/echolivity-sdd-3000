#!/usr/bin/env python3
"""
ECHOLIVITY SDD-3000 -- GenExpr source generator.

Writes src/gen/echolivity_core.genexpr. The engine is written once here; the
per-channel blocks are expanded for L and R so both channels are guaranteed
to run identical code. The resulting GenExpr is what goes into the gen~
codebox inside the .amxd, and it is also what tools/gen2c.py compiles to C
for the offline test-suite. Nothing else is tested.

Coding rules (checked by gen2c.py):
  * every local variable is first assigned at block depth 0
  * a History is never read after it has been written in the same frame
  * no Histories are written inside the while() tick loop
  * no user functions, no ternaries, no '%', no scientific notation
"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "src", "gen", "echolivity_core.genexpr")

# ---------------------------------------------------------------- params
# name, default, min, max, comment
PARAMS = [
    # INPUT (authentic)
    ("p_in_range",   2,    0, 2,    "input ATT  0=-30dBm(Hi-Z, extra amp) 1=-10dBm 2=+4dBm"),
    ("p_in_level",   5,    0, 10,   "input LEVEL, 5 = nominal"),
    # PREAMP CHARACTER (approximation)
    ("p_pre_on",     1,    0, 1,    "preamp character stage on/off"),
    ("p_drive",      0,    0, 24,   "extra drive into op-amp stage, dB"),
    ("p_tone",       0,   -1, 1,    "tone tilt around 800 Hz (+-6 dB)"),
    ("p_pre_comp",   1,    0, 1,    "auto output compensation for drive"),
    ("p_pre_trim",   0,  -24, 24,   "preamp output trim, dB"),
    # DELAY
    ("p_time_ms",  380,    0, 1023, "delay time, ms"),
    ("p_time_mode",  0,    0, 1,    "0=authentic 1 ms steps 1=continuous (modern)"),
    ("p_time_glide", 0,    0, 1,    "0=click-free crossfade 1=glide/pitch-bend (modern)"),
    ("p_sync",       0,    0, 1,    "host tempo sync (modern)"),
    ("p_division",   8,    0, 12,   "note division index (modern); rc5 appends 11 = 1/16T, 12 = 1/32T"),
    ("p_tempo",    120,   20, 999,  "host tempo, BPM (sent by the patcher)"),
    # REGENERATION
    ("p_feedback",   3,    0, 10,   "FEEDBACK 0..10 (loop gain = value/7)"),
    ("p_fb_inv",     0,    0, 1,    "regeneration INV"),
    ("p_lowcut",     0,    0, 3,    "LOW filter 0=FLAT 1=125 2=250 3=500 Hz"),
    ("p_highcut",    0,    0, 3,    "HIGH filter 0=FLAT 1=8k 2=4k 3=2k Hz"),
    ("p_lc_slope",   0,    0, 1,    "LOW slope 0=-3 dB/oct (spec) 1=-6 dB/oct (alt)"),
    ("p_loop_sat",   0,    0, 1,    "0=converter hard clip (authentic) 1=soft loop saturation"),
    ("p_hold",       0,    0, 1,    "HOLD"),
    # v1.0.2-rc4: external regeneration loop through another Live track (modern)
    ("p_fb_route",   0,    0, 2,    "FB ROUTE 0=INT 1=EXT (send outs 3/4 -> return ins 3/4 replaces the internal loop) 2=BOTH"),
    ("p_return",     5,    0, 10,   "EXT RETURN level 0..10 (loop gain = value/7, same law as FEEDBACK)"),
    # v1.0.2-rc5: EXT loop latency compensation and calibration
    ("p_loop_comp",  0,    0, 250,  "LOOP COMP ms: shortens the delay in EXT so each external pass lands on time"),
    ("p_cal",        0,    0, 1,    "CAL trigger (rising edge): measure the external loop's round trip"),
    # MODULATION
    ("p_waveform",   0,    0, 3,    "0=TRI 1=SQUARE 2=RND 3=ENV"),
    ("p_intensity",  0,    0, 10,   "INTENSITY 0..10 (10 = 2:1)"),
    ("p_frequency",  3,    0, 10,   "FREQUENCY 0..10 -> 0.1..15 Hz"),
    ("p_env_sens",   0,  -24, 24,   "envelope sensitivity dB (modern)"),
    ("p_env_rel", 1440,   20, 5000, "envelope release ms (1440 = service-manual Fig.4)"),
    # EFFECT / OUTPUT
    ("p_balance",    5,    0, 10,   "LEVEL BALANCE 0=direct 5=1:1 10=effect"),
    ("p_out_inv",    0,    0, 1,    "output INV (sum/difference on VARIABLE and +MIX)"),
    ("p_bypass",     0,    0, 1,    "BYPASS: direct only, delay input muted (clears loop)"),
    ("p_out_range",  2,    0, 2,    "output ATT 0=-20 1=-10 2=+4 dBm"),
    ("p_out_mode",   0,    0, 3,    "0=MONO(VAR) 1=STEREO A(DIR/+MIX) 2=STEREO B(+MIX/-MIX) 3=TRUE STEREO"),
    ("p_width",      1,    0, 2,    "stereo width (modern)"),
    ("p_wet_only",   0,    0, 1,    "wet only (modern)"),
    ("p_out_gain",   0,  -24, 12,   "output gain dB (modern)"),
    ("p_converter",  0,    0, 1,    "0=13-bit gain-ranged converter 1=clean (modern)"),
    ("p_hf_comp",    1,    0, 1,    "host-rate resampling droop compensation (engineering, keep on)"),
    # reverse (modern, owner request): 0 = OFF (identical to rc6)
    ("p_reverse",    0,    0, 3,    "REVERSE 0=OFF 1=REV (all repeats) 2=ALT (fwd, rev, fwd...) 3=ALT R (rev, fwd, rev...)"),
]

# -------------------------------------------------------------- constants
MEM = 65536          # 64K words (service manual: 4864 = 65536 x 1 DRAM)
WPMS = 64            # words per ms at the 64 kHz nominal clock
NMAX = 1023 * WPMS   # 65472
HOLD_L = 64512       # hold loop length (words)
HOLD_F = 1024        # hold seam crossfade (words)
K_ADC = 5.011872     # +14 dB: nominal (+4 dBm) -> meter 0 dB (= -3 dB re ADC full scale)
K_DAC = 1.0 / K_ADC
RMEM = 131072        # reverse memory: 2 x 64K words, so a reversed window of up to 1023 ms fits
RV_MIN = 128         # shortest reverse window (2 ms at 64 kHz)


def oc(x):
    """op-amp style soft rail clip, rail = 1.0 (inlined, no user functions)"""
    return f"(({x}) / pow(1 + pow(abs({x}), 5), 0.2))"


def per_ch(text):
    out = []
    for c, ci in (("l", "0"), ("r", "1")):
        out.append(text.replace("$c", c).replace("$i", ci))
    return "\n".join(out)


def tpt_lp(state, G, x, lp):
    """TPT one-pole: writes lp; state updated in-place (local var)."""
    return (f"v_tmp = ({x} - {state}) * {G};\n"
            f"{lp} = v_tmp + {state};\n"
            f"{state} = fixdenorm({lp} + v_tmp);")


INIT_PAIRS = [("s_rg", "t_rg"), ("s_w1", "t_w1"), ("s_lvl", "t_lvl"), ("s_pre", "p_pre_on"),
    ("s_drv", "t_drv"), ("s_tone", "p_tone"), ("s_trim", "t_trim"), ("s_fb", "p_feedback * 0.142857143"),
    ("s_int", "p_intensity * 0.1"), ("s_bal_d", "t_bd"), ("s_bal_w", "t_bw"), ("s_sat", "p_loop_sat"),
    ("s_conv", "p_converter"), ("s_lcs", "p_lc_slope"), ("s_oatt", "t_oatt"),
    ("s_ogain", "pow(10, p_out_gain * 0.05)"), ("s_width", "p_width"), ("s_dir", "t_dir"),
    ("s_m0", "t_m0"), ("s_m1", "t_m1"), ("s_m2", "t_m2"), ("s_m3", "t_m3"), ("s_fbs", "t_fbs"),
    ("s_so", "t_so"), ("s_byp", "t_byp"), ("s_lca", "t_lca"), ("s_hca", "t_hca"),
    ("s_fbi", "t_fbi"), ("s_ret", "t_ret"), ("s_rvo", "t_rvo"), ("s_rvf", "t_rvf")]

import json
HFTAB = os.path.join(HERE, "hfcomp_table.json")


def hf_table():
    if os.path.exists(HFTAB):
        return json.load(open(HFTAB))
    return {"rates": [[48000, 23941, 15000, 0.0, 0.7]]}


def build():
    L = []
    a = L.append
    a("// ECHOLIVITY SDD-3000 -- core DSP (gen~ codebox)")
    a("// Independent homage to the 1982 Korg SDD-3000. Not a Korg product.")
    a("// GENERATED by tools/make_gen.py -- edit the generator, not this file.")
    a("// v1.0.2: HOLD release fix + NaN/Inf protection (see docs/ENGINEERING_CHANGES.md).")
    a("")
    for n, d, lo, hi, c in PARAMS:
        a(f"Param {n}({d}, min={lo}, max={hi});   // {c}")
    a("")
    a(f"Data mem({MEM}, 2);")
    a(f"Data rmem({RMEM}, 2);   // reverse: a copy of the recorded words, twice as long")
    a("@@HISTORIES@@")
    a("")
    body = []
    b = body.append

    # ---------------------------------------------------------- load state
    b("// ---------------------------------------------------- frame setup")
    b("sr = samplerate;")
    b("inv_sr = 1 / sr;")
    b("v_tmp = 0;")
    b("k15 = 1 - exp(-1 / (0.015 * sr));   // 15 ms parameter smoothing")
    b("k5 = 1 - exp(-1 / (0.005 * sr));")
    b("k30 = 1 - exp(-1 / (0.03 * sr));")
    b("")
    b("// cached coefficients (recomputed only when the host rate changes)")
    b("g_pre = h_g_pre; g_de = h_g_de; g_aa = h_g_aa; k_aa1 = h_k_aa1; k_aa2 = h_k_aa2; k_aa3 = h_k_aa3;")
    b("g_dc = h_g_dc; g_tone = h_g_tone; k_pk = h_k_pk;")
    b("eq_b0 = h_eq_b0; eq_b1 = h_eq_b1; eq_b2 = h_eq_b2; eq_a1 = h_eq_a1; eq_a2 = h_eq_a2;")
    b("v_g = 0; hf_fa = 0; hf_f0 = 0; hf_gdb = 0; hf_q = 0; eq_a = 0; eq_w = 0; eq_al = 0; eq_n = 0;")
    b("if (sr != h_sr) {")
    b("    v_g = tan(pi * 10610 / sr);  g_pre = v_g / (1 + v_g);     // pre-emph pole 15 us")
    b("    v_g = tan(pi * 3183 / sr);   g_de = v_g / (1 + v_g);      // de-emph pole 50 us")
    tab = hf_table()["rates"]
    b("    hf_fa = 22000; hf_f0 = 15000; hf_gdb = 0; hf_q = 0.7;")
    rates = sorted(tab)
    if len(rates) == 1:
        r, fa, f0, gdb, q = rates[0]
        b(f"    hf_fa = {fa:.3f}; hf_f0 = {f0:.3f}; hf_gdb = {gdb:.4f}; hf_q = {q:.4f};")
        rates = []
    for i, (r, fa, f0, gdb, q) in enumerate(rates):
        if i < len(rates) - 1:
            mid = (r + rates[i + 1][0]) / 2
            kw = "if" if i == 0 else "else if"
            b(f"    {kw} (sr < {mid:.1f}) {{")
        else:
            b("    else {")
        b(f"        hf_fa = {fa:.3f}; hf_f0 = {f0:.3f}; hf_gdb = {gdb:.4f}; hf_q = {q:.4f};")
        b("    }")
    b("    // RBJ peaking EQ: compensates the host-rate interpolation/averaging droop")
    b("    eq_a = pow(10, hf_gdb * 0.025);")
    b("    eq_w = 2 * pi * min(hf_f0, 0.49 * sr) / sr;")
    b("    eq_al = sin(eq_w) / (2 * hf_q);")
    b("    eq_n = 1 / (1 + eq_al / eq_a);")
    b("    eq_b0 = (1 + eq_al * eq_a) * eq_n;")
    b("    eq_b1 = -2 * cos(eq_w) * eq_n;")
    b("    eq_b2 = (1 - eq_al * eq_a) * eq_n;")
    b("    eq_a1 = eq_b1;")
    b("    eq_a2 = (1 - eq_al / eq_a) * eq_n;")
    b("    v_g = tan(pi * min(hf_fa, 0.45 * sr) / sr);  g_aa = v_g;   // AA / reconstruction 2-pole")
    b("    k_aa1 = 1 / (1 + v_g * (v_g + 1.41421356));")
    b("    k_aa2 = v_g * k_aa1;")
    b("    k_aa3 = v_g * k_aa2;")
    b("    v_g = tan(pi * 5 / sr);      g_dc = v_g / (1 + v_g);      // 5 Hz DC block in loop")
    b("    v_g = tan(pi * 800 / sr);    g_tone = v_g / (1 + v_g);")
    b("    k_pk = exp(-1 / (0.3 * sr));                              // meter release")
    b("}")
    b("v_g = 0;")
    b("")
    # load smoothed values
    for n in ["s_rg", "s_w1", "s_lvl", "s_pre", "s_drv", "s_tone", "s_trim", "s_fb", "s_fbs",
              "s_int", "s_bal_d", "s_bal_w", "s_so", "s_byp", "s_sat", "s_conv", "s_lcs",
              "s_lca", "s_hca", "s_lclg", "s_hclg", "s_oatt", "s_ogain", "s_width", "s_dir",
              "s_m0", "s_m1", "s_m2", "s_m3", "s_hm", "s_fbi", "s_ret", "s_rvo", "s_rvf"]:
        b(f"{n} = h_{n};")
    b("")
    b("// ----------------------------------------------- parameter targets")
    b("t_rg = 1;")
    b("t_w1 = 0;")
    b("if (p_in_range < 0.5) {")
    b("    t_rg = 5.011872;   // -30 range: x10 Hi-Z amp, then same pad as -10")
    b("    t_w1 = 1;")
    b("}")
    b("else if (p_in_range < 1.5) {")
    b("    t_rg = 5.011872;   // -10 range: +14 dB")
    b("}")
    b("t_lvl = (p_in_level * 0.2) * (p_in_level * 0.2);   // LEVEL: 5 -> 0 dB, 10 -> +12 dB (approx. taper)")
    b("t_drv = pow(10, p_drive * 0.05);")
    b("t_trim = pow(10, p_pre_trim * 0.05);")
    b("if (p_pre_comp > 0.5) {")
    b("    t_trim = t_trim / t_drv;")
    b("}")
    b("t_fbs = 1;")
    b("if (p_fb_inv > 0.5) {")
    b("    t_fbs = -1;")
    b("}")
    b("// v1.0.2-rc4: regeneration route. INT: internal loop only (identical to rc3).")
    b("// EXT: the loop leaves on outs 6/7 (device outputs 3/4) and only the return (device inputs 3/4)")
    b("// is regenerated. BOTH: internal loop plus the return.")
    b("t_fbi = 1;")
    b("t_ret = 0;")
    b("if (p_fb_route > 0.5) {")
    b("    t_ret = p_return * 0.142857143;")
    b("}")
    b("if (p_fb_route > 0.5 && p_fb_route < 1.5) {")
    b("    t_fbi = 0;")
    b("}")
    b("t_so = 1;")
    b("if (p_out_inv > 0.5) {")
    b("    t_so = -1;")
    b("}")
    b("// REVERSE: which path takes the reversed tap. Output reversed = every echo heard backwards;")
    b("// feedback reversed = the direction flips on every pass through the loop.")
    b("t_rvo = 0;")
    b("t_rvf = 0;")
    b("if (p_reverse > 0.5 && p_reverse < 1.5) {")
    b("    t_rvo = 1;     // REV")
    b("}")
    b("else if (p_reverse > 1.5 && p_reverse < 2.5) {")
    b("    t_rvf = 1;     // ALT: forward first")
    b("}")
    b("else if (p_reverse > 2.5) {")
    b("    t_rvo = 1;     // ALT R: reversed first")
    b("    t_rvf = 1;")
    b("}")
    b("t_bd = min(1, (10 - p_balance) * 0.2);")
    b("t_bw = min(1, p_balance * 0.2);")
    b("t_dir = 1;")
    b("if (p_wet_only > 0.5) {")
    b("    t_bd = 0;")
    b("    t_dir = 0;")
    b("}")
    b("t_byp = 0;")
    b("if (p_bypass > 0.5) {")
    b("    t_byp = 1;")
    b("    t_bd = 1;")
    b("    t_bw = 0;")
    b("    t_dir = 1;")
    b("}")
    b("t_oatt = 1;")
    b("if (p_out_range < 0.5) {")
    b("    t_oatt = 0.063096;   // -20 dBm: -24 dB re +4")
    b("}")
    b("else if (p_out_range < 1.5) {")
    b("    t_oatt = 0.199526;   // -10 dBm: -14 dB re +4")
    b("}")
    b("t_lca = 0;")
    b("t_lclg = s_lclg;")
    b("if (t_lclg < 1) {")
    b("    t_lclg = 6.965784;")
    b("}")
    b("if (p_lowcut > 2.5) {")
    b("    t_lca = 1;")
    b("    t_lclg = 8.965784;   // log2(500)")
    b("}")
    b("else if (p_lowcut > 1.5) {")
    b("    t_lca = 1;")
    b("    t_lclg = 7.965784;   // log2(250)")
    b("}")
    b("else if (p_lowcut > 0.5) {")
    b("    t_lca = 1;")
    b("    t_lclg = 6.965784;   // log2(125)")
    b("}")
    b("t_hca = 0;")
    b("t_hclg = s_hclg;")
    b("if (t_hclg < 1) {")
    b("    t_hclg = 12.965784;")
    b("}")
    b("if (p_highcut > 2.5) {")
    b("    t_hca = 1;")
    b("    t_hclg = 10.965784;  // log2(2000)")
    b("}")
    b("else if (p_highcut > 1.5) {")
    b("    t_hca = 1;")
    b("    t_hclg = 11.965784;  // log2(4000)")
    b("}")
    b("else if (p_highcut > 0.5) {")
    b("    t_hca = 1;")
    b("    t_hclg = 12.965784;  // log2(8000)")
    b("}")
    b("if (s_lclg < 1) {")
    b("    s_lclg = t_lclg;      // first frame: jump to the selected position")
    b("    s_hclg = t_hclg;")
    b("}")
    b("t_m0 = 0; t_m1 = 0; t_m2 = 0; t_m3 = 0;")
    b("if (p_out_mode > 2.5) {")
    b("    t_m3 = 1;")
    b("}")
    b("else if (p_out_mode > 1.5) {")
    b("    t_m2 = 1;")
    b("}")
    b("else if (p_out_mode > 0.5) {")
    b("    t_m1 = 1;")
    b("}")
    b("else {")
    b("    t_m0 = 1;")
    b("}")
    b("")
    b("// first frame after load: start at the targets (no ramps on load)")
    b("if (h_init < 0.5) {")
    for s_, t_ in INIT_PAIRS:
        b(f"    {s_} = {t_};")
    b("}")
    b("// ------------------------------------------------------- smoothing")
    sm15 = [("s_rg", "t_rg"), ("s_w1", "t_w1"), ("s_lvl", "t_lvl"), ("s_pre", "p_pre_on"),
            ("s_drv", "t_drv"), ("s_tone", "p_tone"), ("s_trim", "t_trim"),
            ("s_fb", "p_feedback * 0.142857143"), ("s_int", "p_intensity * 0.1"),
            ("s_bal_d", "t_bd"), ("s_bal_w", "t_bw"), ("s_sat", "p_loop_sat"),
            ("s_conv", "p_converter"), ("s_lcs", "p_lc_slope"), ("s_oatt", "t_oatt"),
            ("s_ogain", "pow(10, p_out_gain * 0.05)"), ("s_width", "p_width"), ("s_dir", "t_dir"),
            ("s_m0", "t_m0"), ("s_m1", "t_m1"), ("s_m2", "t_m2"), ("s_m3", "t_m3"),
            ("s_fbi", "t_fbi"), ("s_ret", "t_ret")]
    for s, t in sm15:
        b(f"{s} = {s} + ({t} - {s}) * k15;")
    for s, t in [("s_fbs", "t_fbs"), ("s_so", "t_so"), ("s_byp", "t_byp"),
                 ("s_lca", "t_lca"), ("s_hca", "t_hca")]:
        b(f"{s} = {s} + ({t} - {s}) * k5;")
    b("s_lclg = s_lclg + (t_lclg - s_lclg) * k30;")
    b("s_hclg = s_hclg + (t_hclg - s_hclg) * k30;")
    b("")
    b("// switched-filter coefficients: recomputed only while a switch is moving")
    b("g_lc0 = h_g_lc0; g_lc1 = h_g_lc1; g_lc2 = h_g_lc2; g_lc6 = h_g_lc6; g_hc = h_g_hc;")
    b("if (abs(s_lclg - h_lc_done) > 0.00001 || sr != h_sr) {")
    b("    v_g = pow(2, s_lclg);")
    b("    g_lc6 = tan(pi * min(v_g, 0.45 * sr) * inv_sr);  g_lc6 = g_lc6 / (1 + g_lc6);")
    b("    v_g = v_g * 1.25;   // half-order (-3 dB/oct) approximation: 3 pole/zero pairs, 2 oct apart")
    b("    g_lc0 = tan(pi * min(v_g, 0.45 * sr) * inv_sr);  g_lc0 = g_lc0 / (1 + g_lc0);")
    b("    g_lc1 = tan(pi * v_g * 0.25 * inv_sr);  g_lc1 = g_lc1 / (1 + g_lc1);")
    b("    g_lc2 = tan(pi * v_g * 0.0625 * inv_sr);  g_lc2 = g_lc2 / (1 + g_lc2);")
    b("}")
    b("if (abs(s_hclg - h_hc_done) > 0.00001 || sr != h_sr) {")
    b("    v_g = pow(2, s_hclg);")
    b("    g_hc = tan(pi * min(v_g, 0.45 * sr) * inv_sr);  g_hc = g_hc / (1 + g_hc);")
    b("}")
    b("v_g = 0;")
    b("// REVERSE: 25 ms linear ramps that land exactly on 0 / 1, smoothstep-weighted")
    b("rv_step = inv_sr / 0.025;")
    b("s_rvo = s_rvo + clamp(t_rvo - s_rvo, -rv_step, rv_step);")
    b("s_rvf = s_rvf + clamp(t_rvf - s_rvf, -rv_step, rv_step);")
    b("g_rvo = s_rvo * s_rvo * (3 - 2 * s_rvo);")
    b("g_rvf = s_rvf * s_rvf * (3 - 2 * s_rvf);")
    b("rv_on = 0;")
    b("if (s_rvo > 0 || s_rvf > 0 || t_rvo > 0.5 || t_rvf > 0.5) {")
    b("    rv_on = 1;")
    b("}")
    b("")

    # ---------------------------------------------------------------- input
    b("// ============================================================ INPUT")
    b("in_l = clamp(fixnan(in1), -1000, 1000);   // v1.0.2: NaN -> 0, +-inf -> +-1000 (+60 dBFS); valid audio unchanged")
    b("in_r = clamp(fixnan(in2), -1000, 1000);")
    b("ret_l = clamp(fixnan(in3), -1000, 1000);   // v1.0.2-rc4: EXT loop return (device inputs 3/4)")
    b("ret_r = clamp(fixnan(in4), -1000, 1000);")
    b("// rc5: CAL. Fade the external loop out (20 ms), wait (30 ms), send one click on outputs 3/4, time its")
    b("// arrival on inputs 3/4 (max 500 ms), fade back in. Result (ms, or -1 = not found) on out8 for 100 ms.")
    b("cal_st = h_cal_st; cal_n = h_cal_n; cal_m = h_cal_m; cal_env = h_cal_env; cal_res = h_cal_res; cal_hold = h_cal_hold;")
    b("cal_prev = p_cal;")
    b("if (p_cal > 0.5 && h_cal_prev < 0.5 && cal_st < 0.5 && p_fb_route > 0.5) {")
    b("    cal_st = 1;")
    b("    cal_n = 0;")
    b("}")
    b("cal_click = 0;")
    b("cal_a = abs(ret_l) + abs(ret_r);")
    b("if (cal_st > 0.5) {")
    b("    cal_n = cal_n + 1;")
    b("}")
    b("if (cal_st > 0.5 && cal_st < 1.5) {")
    b("    cal_m = min(cal_m + 50 / sr, 1);")
    b("    if (cal_n > 0.05 * sr) {")
    b("        cal_st = 2;")
    b("        cal_n = 0;")
    b("        cal_env = 0;")
    b("    }")
    b("}")
    b("else if (cal_st > 1.5 && cal_st < 2.5) {")
    b("    if (cal_n < 1.5) {")
    b("        cal_click = 0.9;")
    b("    }")
    b("    if (cal_n > 1.5 && cal_a > 0.25 && cal_a > 4 * cal_env) {")
    b("        cal_res = (cal_n - 1) * 1000 / sr;")
    b("        cal_hold = 0.1 * sr;")
    b("        cal_st = 3;")
    b("        cal_n = 0;")
    b("    }")
    b("    else if (cal_n > 0.5 * sr) {")
    b("        cal_res = -1;")
    b("        cal_hold = 0.1 * sr;")
    b("        cal_st = 3;")
    b("        cal_n = 0;")
    b("    }")
    b("    cal_env = cal_env + (cal_a - cal_env) * 0.002;")
    b("}")
    b("else if (cal_st > 2.5) {")
    b("    cal_m = max(cal_m - 50 / sr, 0);")
    b("    if (cal_m < 0.0000001) {")
    b("        cal_m = 0;")
    b("        cal_st = 0;")
    b("    }")
    b("}")
    b("cal_out = -2;")
    b("if (cal_hold > 0.5) {")
    b("    cal_out = cal_res;")
    b("    cal_hold = cal_hold - 1;")
    b("}")
    b("cal_live = 1 - cal_m;")
    b("x_m = (in_l + in_r) * 0.5;")
    b("x_l = x_m;")
    b("x_r = x_m;")
    b("if (s_m3 > 0.000001) {")
    b("    x_l = x_m + (in_l - x_m) * s_m3;     // TRUE STEREO (modern) keeps L/R separate")
    b("    x_r = x_m + (in_r - x_m) * s_m3;")
    b("}")
    b("st_tone_l = h_st_tone_l; st_tone_r = h_st_tone_r;")
    pre = """
// -- channel $c : attenuator / Hi-Z amp / LEVEL / op-amp stage (approximation)
s1c_$c = x_$c + (OC1 - x_$c) * s_w1;          // -30 range: x10 Hi-Z amp with rail clip
s1l_$c = x_$c * (1 + 9 * s_w1);                // same, linear (character off)
v_tmp = (s1c_$c * s_rg * s_lvl - st_tone_$c) * g_tone;
tl_$c = v_tmp + st_tone_$c;
st_tone_$c = fixdenorm(tl_$c + v_tmp);
th_$c = s1c_$c * s_rg * s_lvl - tl_$c;
tt_$c = tl_$c * pow(2, -s_tone) + th_$c * pow(2, s_tone);     // +-6 dB tilt
dv_$c = tt_$c * s_drv;
ac_$c = OC2 * s_trim;                          // amp B rail clip (+17 dB over nominal at LEVEL 5)
al_$c = s1l_$c * s_rg * s_lvl;
a_$c = al_$c + (ac_$c - al_$c) * s_pre;       // preamp output = DIRECT signal
"""
    pre = pre.replace("OC1", oc("x_$c * 10")).replace("OC2", oc("dv_$c"))
    b(per_ch(pre))
    b("")

    # ------------------------------------------------------------ modulation
    b("// ======================================================= MODULATION")
    b("lph = h_lph; rnd_t = h_rnd_t; rnd1 = h_rnd1; rnd2 = h_rnd2; envf = h_envf; m_s = h_m_s;")
    b("f_hz = 0.1 * pow(150, p_frequency * 0.1);   // 0 -> 0.1 Hz (10 s), 10 -> 15 Hz")
    b("lph = lph + f_hz * inv_sr;")
    b("lwrap = 0;")
    b("if (lph >= 1) {")
    b("    lph = lph - 1;")
    b("    lwrap = 1;")
    b("}")
    b("tri = 1 - abs(2 * lph - 1);")
    b("m_tri = (sqrt(tri * tri + 0.0144) - 0.12) * 1.127172;   // sharp peak, rounded trough (SM Fig.3)")
    b("m_sq = 0;")
    b("if (lph >= 0.5) {")
    b("    m_sq = 1;")
    b("}")
    b("if (lwrap > 0.5) {")
    b("    rnd_t = noise() * 0.5 + 0.5;    // new random level once per LFO cycle")
    b("}")
    b("k_rnd = 1 - exp(-4 * f_hz * inv_sr);   // 'integrated' (smoothed) S&H")
    b("rnd1 = rnd1 + (rnd_t - rnd1) * k_rnd;")
    b("rnd2 = fixdenorm(rnd2 + (rnd1 - rnd2) * k_rnd);")
    b("e_in = max(abs(a_l), abs(a_r)) * 5.011872 * pow(10, p_env_sens * 0.05);")
    b("if (e_in > envf) {")
    b("    envf = envf + (e_in - envf) * (1 - exp(-1 / (0.002 * sr)));")
    b("}")
    b("else {")
    b("    envf = fixdenorm(envf + (e_in - envf) * (1 - exp(-1 / (p_env_rel * 0.001 * sr))));")
    b("}")
    b("m_env = clamp(envf * 1.412538, 0, 1);    // nominal level (meter 0 dB) = full swing")
    b("m_raw = m_tri;")
    b("if (p_waveform > 2.5) {")
    b("    m_raw = m_env;")
    b("}")
    b("else if (p_waveform > 1.5) {")
    b("    m_raw = rnd2;")
    b("}")
    b("else if (p_waveform > 0.5) {")
    b("    m_raw = m_sq;")
    b("}")
    b("m_s = m_s + (m_raw - m_s) * (1 - exp(-1 / (0.0007 * sr)));   // VCO control lag")
    b("fv = 64000 * (1 + s_int * m_s);    // memory clock: 64 kHz nominal, up to 2:1 (delay -> 50%)")
    b("")

    # ------------------------------------------------------------- delay time
    b("// ======================================================= DELAY TIME")
    b("ms = p_time_ms;")
    b("if (p_time_mode < 0.5) {")
    b("    ms = floor(p_time_ms + 0.5);     // authentic 1 ms steps")
    b("}")
    b("beats = 4;")
    b("if (p_sync > 0.5) {")
    # index: 0 1/32, 1 1/16, 2 1/8T, 3 1/8, 4 1/4T, 5 1/8D, 6 1/4, 7 1/2T, 8 1/4D, 9 1/2, 10 1/1 (else branch);
    # rc5 appends 11 1/16T and 12 1/32T (existing indices unchanged for old Sets and programs)
    divs = [0.125, 0.25, 1/3, 0.5, 2/3, 0.75, 1.0, 4/3, 1.5, 2.0]
    for i, v in enumerate(divs):
        kw = "if" if i == 0 else "else if"
        b(f"    {kw} (p_division < {i}.5) {{")
        b(f"        beats = {v:.9f};")
        b("    }")
    b("    if (p_division > 10.5 && p_division < 11.5) {")
    b("        beats = 0.166666667;     // rc5: 1/16T")
    b("    }")
    b("    if (p_division > 11.5) {")
    b("        beats = 0.083333333;     // rc5: 1/32T")
    b("    }")
    b("    ms = clamp(60000 / max(p_tempo, 20) * beats, 0, 1023);")
    b("}")
    b("ms_disp = ms;")
    b("// rc5: LOOP COMP. In EXT the external pass adds Live's routing latency; shorten the internal delay")
    b("// by the same amount so the repeat period equals TIME. Not applied in INT or BOTH.")
    b("if (p_loop_comp > 0 && p_fb_route > 0.5 && p_fb_route < 1.5) {")
    b("    ms = max(ms - p_loop_comp, 1);")
    b("}")
    b(f"n_tgt = fixnan(clamp(ms * {WPMS}, 0, {NMAX}));")
    b("na = h_na; nb = h_nb; xf = h_xf; xdir = h_xdir; ns = h_ns;")
    b("act = 0;")
    b("xstep = 0;")
    b("if (p_time_glide > 0.5) {")
    b("    ns = ns + (n_tgt - ns) * (1 - exp(-1 / (0.12 * sr)));")
    b("    na = ns;")
    b("    nb = ns;")
    b("    xf = 0;")
    b("    xdir = 0;")
    b("}")
    b("else {")
    b("    if (abs(xf - xdir) < 0.0000001) {")
    b("        act = na;")
    b("        if (xdir > 0.5) {")
    b("            act = nb;")
    b("        }")
    b("        if (abs(n_tgt - act) > 0.001) {")
    b("            if (xdir > 0.5) {")
    b("                na = n_tgt;")
    b("                xdir = 0;")
    b("            }")
    b("            else {")
    b("                nb = n_tgt;")
    b("                xdir = 1;")
    b("            }")
    b("        }")
    b("    }")
    b("    xstep = inv_sr / 0.025;     // 25 ms equal-power crossfade between taps")
    b("    xf = xf + clamp(xdir - xf, -xstep, xstep);")
    b("    ns = na + (nb - na) * xf;")
    b("}")
    b(f"rv_len = clamp(floor(ns + 0.5), {RV_MIN}, {RMEM // 2});   // reverse window = the current delay")
    b("g_a = cos(xf * 1.570796327);")
    b("g_b = sin(xf * 1.570796327);")
    b("")

    # -------------------------------------------------------------- hold
    b("// ============================================================= HOLD")
    b("// v1.0.2: state machine  hst 0 = normal, 1 = held, 2 = releasing (loop audible),")
    b("// 3 = releasing, loop faded early because the HOLD reader would reach new audio (delays > ~944 ms).")
    b("// Engage is unchanged from v1.0.1. On release the HOLD loop keeps playing while the")
    b("// writer restarts just behind the HOLD reader; once the normal tap reads only newly")
    b("// written memory (one delay time later) the loop crossfades out over 10 ms.")
    b("w = h_w; hpos = h_hpos; hbase = h_hbase; hst = h_hst; relk = h_relk; g_w = h_g_w; gnt = h_gnt;")
    b("hshape = h_hshape;   // 1 while a release fade (or its reversal) is in progress: smoothstep weighting")
    b("if (h_init < 0.5) {")
    b("    g_w = 1;")
    b("    gnt = 1;")
    b("}")
    b("hold_on = 0;")
    b("n_dom = 0;")
    b("hr0 = 0;")
    b("if (p_hold > 0.5) {")
    b("    hold_on = 1;")
    b("}")
    b("if (hold_on > 0.5 && hst < 0.5) {")
    b("    if (s_hm > 0.000001) {")
    b("        hst = 1;     // re-engaged while the previous loop is still audible: keep it, no jump")
    b("    }")
    b("    else {")
    b("        hbase = w;   // loop = the last 1008 ms written; playback continues from the current tap")
    b("        n_dom = na;")
    b("        if (g_b > g_a) {")
    b("            n_dom = nb;")
    b("        }")
    b(f"        hpos = clamp(floor({HOLD_L} - n_dom + 0.5), 0, {HOLD_L - 1});")
    b("        g_w = 0;     // memory writes stop immediately (as v1.0.1)")
    b("        hst = 1;")
    b("    }")
    b("}")
    b("else if (hold_on > 0.5 && hst > 1.5) {")
    b("    hst = 1;         // re-engaged during the release window: keep the loop, fade the writes out")
    b("}")
    b("else if (hold_on < 0.5 && hst > 0.5 && hst < 1.5 && s_hm >= 1) {")
    b(f"    hr0 = hbase - {HOLD_L} + hpos - 1;   // writer restarts one word behind the HOLD reader")
    b("    if (hr0 < 0) {")
    b(f"        hr0 = hr0 + {MEM};")
    b("    }")
    b("    w = hr0;")
    b("    relk = 0;")
    b("    hst = 2;")
    b("}")
    b("hm_t = 0;")
    b("hm_step = inv_sr / 0.010;      // release: 10 ms crossfade back to the normal tap")
    b("if (hst > 0.5 && hst < 2.5) {")
    b("    hm_t = 1;")
    b("    hm_step = inv_sr / 0.005;  // engage: 5 ms (as v1.0.1)")
    b("}")
    b("s_hm = s_hm + clamp(hm_t - s_hm, -hm_step, hm_step);")
    b("if (s_hm >= 1 || s_hm <= 0) {")
    b("    hshape = 0;")
    b("}")
    b("hm_w = s_hm;                   // engage / held: linear (as v1.0.1)")
    b("if (hshape > 0.5) {")
    b("    hm_w = s_hm * s_hm * (3 - 2 * s_hm);   // release fade: smoothstep, no slope corners; stays")
    b("}                                          // smoothstep if HOLD is pressed again mid-fade (continuous)")
    b("// normal-tap gain: muted while releasing until the tap reads only new audio")
    b("gnt_t = 1;")
    b("if (hst > 1.5) {")
    b("    gnt_t = 0;")
    b("}")
    b("if (gnt_t > 0.5 && s_hm >= 1) {")
    b("    gnt = 1;                   // loop still fully audible: switch silently")
    b("}")
    b("gnt = gnt + clamp(gnt_t - gnt, -inv_sr / 0.010, inv_sr / 0.010);")
    b("gnt_w = gnt * gnt * (3 - 2 * gnt);")
    b("w_tgt = 1;")
    b("if (hst > 0.5 && hst < 1.5) {")
    b("    w_tgt = 0;")
    b("}")
    b("")

    # --------------------------------------------------------- ADC chain
    b("// ======================================== FEEDBACK SUM -> A/D chain")
    b("fb_l = h_fb_l; fb_r = h_fb_r;")
    b("st_pre_l = h_st_pre_l; st_pre_r = h_st_pre_r; st_dc_l = h_st_dc_l; st_dc_r = h_st_dc_r;")
    b("ia1_l = h_ia1_l; ia2_l = h_ia2_l; ia1_r = h_ia1_r; ia2_r = h_ia2_r;")
    adc = """
d_$c = (a_$c + fb_$c) * 5.011872;              // summing amp -> converter scale (meter tap)
dg_$c = d_$c * (1 - s_byp);                    // BYPASS grounds the converter input
v_tmp = (dg_$c - st_pre_$c) * g_pre;           // pre-emphasis (50/15 us shelf, +10.5 dB HF)
pl_$c = v_tmp + st_pre_$c;
st_pre_$c = fixdenorm(pl_$c + v_tmp);
pe_$c = pl_$c + 3.333333 * (dg_$c - pl_$c);
v3_$c = pe_$c - ia2_$c;                        // anti-alias LPF (2-pole Butterworth)
v1_$c = k_aa1 * ia1_$c + k_aa2 * v3_$c;
v2_$c = ia2_$c + k_aa2 * ia1_$c + k_aa3 * v3_$c;
ia1_$c = fixdenorm(2 * v1_$c - ia1_$c);
ia2_$c = fixdenorm(2 * v2_$c - ia2_$c);
v_tmp = (v2_$c - st_dc_$c) * g_dc;             // 5 Hz DC block (no DC accumulation)
dcl_$c = v_tmp + st_dc_$c;
st_dc_$c = fixdenorm(dcl_$c + v_tmp);
xs_$c = v2_$c - dcl_$c;
xsat_$c = 0.98 * OC3;
xc_$c = xs_$c + (xsat_$c - xs_$c) * s_sat;    // optional soft loop saturation
"""
    adc = adc.replace("OC3", oc("xs_$c * 1.0204"))
    b(per_ch(adc))
    b("pk = max(abs(d_l), abs(d_r));")
    b("mtr = h_mtr * k_pk;")
    b("if (pk > mtr) {")
    b("    mtr = pk;")
    b("}")
    b("")

    # --------------------------------------------------------- tick loop
    b("// ================================== MEMORY CLOCK EMULATION (ticks)")
    b("// The 64K-word memory runs on its own (modulated) clock. Every tick")
    b("// converts the interpolated input, writes one word and reads the taps;")
    b("// the DAC output is a zero-order hold, integrated over the host sample.")
    b("ph = h_ph;")
    b("xp_l = h_xp_l; xp_r = h_xp_r;")
    b("dac_l = h_dac_l; dac_r = h_dac_r;")
    b("inc = fv * inv_sr;")
    b("tdt = 1 / inc;")
    b("tt = (1 - ph) * tdt;")
    b("tl = 0;")
    b("nt = 0;")
    b("acc_l = 0; acc_r = 0;")
    b("lsb_q = 1 - s_conv;")
    b("rw = h_rw; rka = h_rka; rkb = h_rkb; rla = h_rla; rlb = h_rlb;")
    b("dacr_l = h_dacr_l; dacr_r = h_dacr_r;")
    b("accr_l = 0; accr_r = 0;")
    b(f"if (rla < {RV_MIN - 0.5}) {{")
    b("    rla = rv_len;")
    b("    rka = 0;")
    b("}")
    b(f"if (rlb < {RV_MIN - 0.5}) {{")
    b("    rlb = rv_len;")
    b("    rkb = floor(rv_len * 0.5);   // second reader half a window later: the two Hann windows sum to 1")
    b("}")
    for v in ["xi_l", "xi_r", "q_l", "q_r", "ra", "ia", "fa", "ib", "rb", "jb", "fb2", "jb2",
              "ta_l", "ta_r", "tb_l", "tb_r", "hr", "hr2", "hg", "hv_l", "hv_r", "wl", "wr", "ia2", "q13_l", "q13_r",
              "g_ws", "rq_l", "rq_r", "rra", "rrb", "rga", "rgb", "rgs", "rvl", "rvr"]:
        b(f"{v} = 0;")
    b("while (tt < 1 && nt < 8) {")
    b("    acc_l = acc_l + dac_l * (tt - tl);")
    b("    acc_r = acc_r + dac_r * (tt - tl);")
    b("    accr_l = accr_l + dacr_l * (tt - tl);")
    b("    accr_r = accr_r + dacr_r * (tt - tl);")
    for c in "lr":
        b(f"    xi_{c} = clamp(xp_{c} + (xc_{c} - xp_{c}) * tt, -1, 0.999755859);   // converter full scale")
        b(f"    if (abs(xi_{c}) < 0.5) {{")
        b(f"        q13_{c} = floor(xi_{c} * 4096 + 0.5) * 0.000244140625;   // gain-ranged: +6 dB before the 12-bit converter")
        b("    }")
        b("    else {")
        b(f"        q13_{c} = floor(xi_{c} * 2048 + 0.5) * 0.00048828125;    // 12-bit")
        b("    }")
        b(f"    q_{c} = xi_{c} + (q13_{c} - xi_{c}) * lsb_q;")
    b("    q_l = fixnan(q_l);")
    b("    q_r = fixnan(q_r);")
    b("    rq_l = q_l;")
    b("    rq_r = q_r;")
    b("    if (g_w > 0.000001) {")
    b("        if (g_w < 0.999999) {")
    b("            g_ws = g_w * g_w * (3 - 2 * g_w);   // 4 ms smoothstep write fade (HOLD transitions only)")
    b("            q_l = peek(mem, w, 0) + (q_l - peek(mem, w, 0)) * g_ws;")
    b("            q_r = peek(mem, w, 1) + (q_r - peek(mem, w, 1)) * g_ws;")
    b("            rq_l = peek(rmem, rw, 0) + (rq_l - peek(rmem, rw, 0)) * g_ws;")
    b("            rq_r = peek(rmem, rw, 1) + (rq_r - peek(rmem, rw, 1)) * g_ws;")
    b("        }")
    b("        poke(mem, q_l, w, 0);")
    b("        poke(mem, q_r, w, 1);")
    b("        poke(rmem, rq_l, rw, 0);    // reverse memory records exactly what the main memory records")
    b("        poke(rmem, rq_r, rw, 1);")
    b("    }")
    b("    rra = rw - 2 * rka;              // reverse readers move backwards: age 2k, window centre = delay")
    b("    if (rra < 0) {")
    b(f"        rra = rra + {RMEM};")
    b("    }")
    b("    rrb = rw - 2 * rkb;")
    b("    if (rrb < 0) {")
    b(f"        rrb = rrb + {RMEM};")
    b("    }")
    b("    if (rv_on > 0.5) {")
    b("        rga = 0.5 - 0.5 * cos(6.283185307 * rka / rla);")
    b("        rgb = 0.5 - 0.5 * cos(6.283185307 * rkb / rlb);")
    b("        rgs = max(rga + rgb, 0.25);   // = 1 while the window length is steady")
    b("        rvl = (peek(rmem, rra, 0) * rga + peek(rmem, rrb, 0) * rgb) / rgs;")
    b("        rvr = (peek(rmem, rra, 1) * rga + peek(rmem, rrb, 1) * rgb) / rgs;")
    b("    }")
    b("    if (g_w > 0.000001) {")
    b("        rka = rka + 1;               // readers advance only while recording (frozen during HOLD)")
    b("        if (rka >= rla) {")
    b("            rka = 0;")
    b("            rla = rv_len;")
    b("        }")
    b("        rkb = rkb + 1;")
    b("        if (rkb >= rlb) {")
    b("            rkb = 0;")
    b("            rlb = rv_len;")
    b("        }")
    b("        rw = rw + 1;")
    b(f"        if (rw >= {RMEM}) {{")
    b(f"            rw = rw - {RMEM};")
    b("        }")
    b("    }")
    b("    g_w = g_w + clamp(w_tgt - g_w, -0.00390625, 0.00390625);")
    b("    relk = relk + 1;")
    b("    if (relk > 70000) {")
    b("        relk = 70000;")
    b("    }")
    b("    ra = w - na;")
    b("    if (ra < 0) {")
    b(f"        ra = ra + {MEM};")
    b("    }")
    b("    ia = floor(ra);")
    b("    fa = ra - ia;")
    b("    ia2 = ia + 1;")
    b(f"    if (ia2 >= {MEM}) {{")
    b(f"        ia2 = ia2 - {MEM};")
    b("    }")
    b("    ta_l = peek(mem, ia, 0) * (1 - fa) + peek(mem, ia2, 0) * fa;")
    b("    ta_r = peek(mem, ia, 1) * (1 - fa) + peek(mem, ia2, 1) * fa;")
    b("    tb_l = ta_l;")
    b("    tb_r = ta_r;")
    b("    if (xf > 0.0000001 && xf < 0.9999999) {")
    b("        rb = w - nb;")
    b("        if (rb < 0) {")
    b(f"            rb = rb + {MEM};")
    b("        }")
    b("        jb = floor(rb);")
    b("        fb2 = rb - jb;")
    b("        jb2 = jb + 1;")
    b(f"        if (jb2 >= {MEM}) {{")
    b(f"            jb2 = jb2 - {MEM};")
    b("        }")
    b("        tb_l = peek(mem, jb, 0) * (1 - fb2) + peek(mem, jb2, 0) * fb2;")
    b("        tb_r = peek(mem, jb, 1) * (1 - fb2) + peek(mem, jb2, 1) * fb2;")
    b("        wl = ta_l * g_a + tb_l * g_b;")
    b("        wr = ta_r * g_a + tb_r * g_b;")
    b("    }")
    b("    else {")
    b("        wl = ta_l;")
    b("        wr = ta_r;")
    b("        if (xf >= 0.9999999) {")
    b("            rb = w - nb;")
    b("            if (rb < 0) {")
    b(f"                rb = rb + {MEM};")
    b("            }")
    b("            jb = floor(rb);")
    b("            fb2 = rb - jb;")
    b("            jb2 = jb + 1;")
    b(f"            if (jb2 >= {MEM}) {{")
    b(f"                jb2 = jb2 - {MEM};")
    b("            }")
    b("            wl = peek(mem, jb, 0) * (1 - fb2) + peek(mem, jb2, 0) * fb2;")
    b("            wr = peek(mem, jb, 1) * (1 - fb2) + peek(mem, jb2, 1) * fb2;")
    b("        }")
    b("    }")
    b("    if (gnt_w < 1) {")
    b("        wl = wl * gnt_w;")
    b("        wr = wr * gnt_w;")
    b("        rvl = rvl * gnt_w;")
    b("        rvr = rvr * gnt_w;")
    b("    }")
    b("    if (s_hm > 0.000001) {")
    b(f"        hr = hbase - {HOLD_L} + hpos;")
    b("        if (hr < 0) {")
    b(f"            hr = hr + {MEM};")
    b("        }")
    b("        hv_l = peek(mem, hr, 0);")
    b("        hv_r = peek(mem, hr, 1);")
    b(f"        if (hpos >= {HOLD_L - HOLD_F}) {{")
    b(f"            hg = (hpos - {HOLD_L - HOLD_F}) * {1.0/HOLD_F:.12f};   // seam crossfade")
    b(f"            hr2 = hr - {HOLD_L};")
    b("            if (hr2 < 0) {")
    b(f"                hr2 = hr2 + {MEM};")
    b("            }")
    b("            hv_l = hv_l * sqrt(1 - hg) + peek(mem, hr2, 0) * sqrt(hg);")
    b("            hv_r = hv_r * sqrt(1 - hg) + peek(mem, hr2, 1) * sqrt(hg);")
    b("        }")
    b("        wl = wl + (hv_l - wl) * hm_w;")
    b("        wr = wr + (hv_r - wr) * hm_w;")
    b("        rvl = rvl + (hv_l - rvl) * hm_w;   // HOLD plays forwards in every REVERSE mode")
    b("        rvr = rvr + (hv_r - rvr) * hm_w;")
    b("    }")
    b("    dac_l = wl;")
    b("    dac_r = wr;")
    b("    dacr_l = rvl;")
    b("    dacr_r = rvr;")
    b("    w = w + 1;")
    b(f"    if (w >= {MEM}) {{")
    b(f"        w = w - {MEM};")
    b("    }")
    b("    hpos = hpos + 1;")
    b(f"    if (hpos >= {HOLD_L}) {{")
    b(f"        hpos = hpos - {HOLD_L};")
    b("    }")
    b("    tl = tt;")
    b("    tt = tt + tdt;")
    b("    nt = nt + 1;")
    b("}")
    b("acc_l = acc_l + dac_l * (1 - tl);")
    b("acc_r = acc_r + dac_r * (1 - tl);")
    b("accr_l = accr_l + dacr_l * (1 - tl);")
    b("accr_r = accr_r + dacr_r * (1 - tl);")
    b("hra = 0;")
    b("if (hst > 1.5) {")
    b(f"    hra = hbase - {HOLD_L} + hpos - w;   // how far the HOLD reader is ahead of the writer")
    b("    if (hra < 0) {")
    b(f"        hra = hra + {MEM};")
    b("    }")
    b("    if (relk >= max(na, nb) + 3) {")
    b("        if (hst < 2.5) {")
    b("            hshape = 1;")
    b("        }")
    b("        hst = 0;     // the normal tap now reads only new audio -> crossfade the loop out")
    b("    }")
    b(f"    else if (relk + 3072 >= {MEM} - hra - {HOLD_F} && hst < 2.5) {{")
    b("        hshape = 1;")
    b("        hst = 3;     // reader would reach new audio first (delay > ~944 ms): fade the loop out now")
    b("    }")
    b("}")
    b("ph = ph + inc - nt;")
    b("if (ph >= 1) {")
    b("    ph = 0.999999;")
    b("}")
    b("if (ph < 0) {")
    b("    ph = 0;")
    b("}")
    b("")

    # --------------------------------------------------------- DAC chain
    b("// ===================== D/A -> LPF -> DE-EMPHASIS -> LOW/HIGH filters")
    b("ib1_l = h_ib1_l; ib2_l = h_ib2_l; ib1_r = h_ib1_r; ib2_r = h_ib2_r;")
    b("st_de_l = h_st_de_l; st_de_r = h_st_de_r;")
    b("eqz1_l = h_eqz1_l; eqz2_l = h_eqz2_l; eqz1_r = h_eqz1_r; eqz2_r = h_eqz2_r;")
    b("lc0_l = h_lc0_l; lc1_l = h_lc1_l; lc2_l = h_lc2_l; lc6_l = h_lc6_l; hcs_l = h_hcs_l;")
    b("lc0_r = h_lc0_r; lc1_r = h_lc1_r; lc2_r = h_lc2_r; lc6_r = h_lc6_r; hcs_r = h_hcs_r;")
    dac = """
u3_$c = acc_$c - ib2_$c;                       // reconstruction LPF (2-pole Butterworth)
u1_$c = k_aa1 * ib1_$c + k_aa2 * u3_$c;
u2_$c = ib2_$c + k_aa2 * ib1_$c + k_aa3 * u3_$c;
ib1_$c = fixdenorm(2 * u1_$c - ib1_$c);
ib2_$c = fixdenorm(2 * u2_$c - ib2_$c);
eqy_$c = eq_b0 * u2_$c + eqz1_$c;                // droop compensation (TDF-II biquad)
eqz1_$c = fixdenorm(eq_b1 * u2_$c - eq_a1 * eqy_$c + eqz2_$c);
eqz2_$c = fixdenorm(eq_b2 * u2_$c - eq_a2 * eqy_$c);
uq_$c = u2_$c + (eqy_$c - u2_$c) * p_hf_comp;
v_tmp = (uq_$c - st_de_$c) * g_de;             // de-emphasis
dl_$c = v_tmp + st_de_$c;
st_de_$c = fixdenorm(dl_$c + v_tmp);
y_$c = (dl_$c + 0.3 * (uq_$c - dl_$c)) * 0.199526231;   // back to analog nominal
v_tmp = (y_$c - lc0_$c) * g_lc0;               // LOW cut: half-order (-3 dB/oct)
lp0_$c = v_tmp + lc0_$c;
lc0_$c = fixdenorm(lp0_$c + v_tmp);
z0_$c = (y_$c - lp0_$c) + 0.5 * lp0_$c;
v_tmp = (z0_$c - lc1_$c) * g_lc1;
lp1_$c = v_tmp + lc1_$c;
lc1_$c = fixdenorm(lp1_$c + v_tmp);
z1_$c = (z0_$c - lp1_$c) + 0.5 * lp1_$c;
v_tmp = (z1_$c - lc2_$c) * g_lc2;
lp2_$c = v_tmp + lc2_$c;
lc2_$c = fixdenorm(lp2_$c + v_tmp);
z2_$c = (z1_$c - lp2_$c) + 0.5 * lp2_$c;
v_tmp = (y_$c - lc6_$c) * g_lc6;               // LOW cut: alternative first-order (-6 dB/oct)
lp6_$c = v_tmp + lc6_$c;
lc6_$c = fixdenorm(lp6_$c + v_tmp);
z6_$c = y_$c - lp6_$c;
zl_$c = z2_$c + (z6_$c - z2_$c) * s_lcs;
lo_$c = y_$c + (zl_$c - y_$c) * s_lca;
v_tmp = (lo_$c - hcs_$c) * g_hc;               // HIGH cut: first-order (-6 dB/oct)
hl_$c = v_tmp + hcs_$c;
hcs_$c = fixdenorm(hl_$c + v_tmp);
wet_$c = lo_$c + (hl_$c - lo_$c) * s_hca;
"""
    b(per_ch(dac))
    # REVERSE: the same D/A chain and LOW/HIGH filters for the reversed tap, with its own states
    rdac = re.sub(r"\b([A-Za-z0-9_]+?)_\$c\b", r"\1r_$c", dac)
    rlhs = sorted(set(re.findall(r"^\s*([A-Za-z0-9_]+r)_\$c\s*=", rdac, re.M)))
    rstate = ["ib1r", "ib2r", "st_der", "eqz1r", "eqz2r", "lc0r", "lc1r", "lc2r", "lc6r", "hcsr"]
    for c in "lr":
        b(" ".join(f"{v}_{c} = h_{v}_{c};" for v in rstate))
    b("// ----- REVERSE tap: own D/A chain, computed only while a REVERSE mode is (fading) on")
    tmp = [f"{v}_{c}" for v in rlhs for c in "lr" if v not in rstate]
    b(" ".join(f"{v} = 0;" for v in tmp))
    b("if (rv_on > 0.5) {")
    for line in per_ch(rdac).splitlines():
        b("    " + line if line.strip() else line)
    b("}")
    b("else {")
    for c in "lr":
        b("    " + " ".join(f"{v}_{c} = 0;" for v in rstate))
    b("}")
    b("wo_l = wet_l; wo_r = wet_r;     // output path")
    b("wf_l = wet_l; wf_r = wet_r;     // regeneration path (and the EXT send)")
    b("if (rv_on > 0.5) {")
    b("    wo_l = wet_l + (wetr_l - wet_l) * g_rvo;")
    b("    wo_r = wet_r + (wetr_r - wet_r) * g_rvo;")
    b("    wf_l = wet_l + (wetr_l - wet_l) * g_rvf;")
    b("    wf_r = wet_r + (wetr_r - wet_r) * g_rvf;")
    b("}")
    b(per_ch("fbn_$c = wf_$c * s_fb * s_fbs * s_fbi + ret_$c * s_ret * cal_live;   // regeneration: internal + EXT return"))
    b("")

    # ------------------------------------------------------------- output
    b("// ============================================================ OUTPUT")
    b("mx_l = a_l * s_bal_d + s_so * wo_l * s_bal_w;     // VARIABLE / +MIX")
    b("mn_l = a_l * s_bal_d - wo_l * s_bal_w;            // -MIX (always difference)")
    b("mx_r = a_r * s_bal_d + s_so * wo_r * s_bal_w;")
    b("dr_l = a_l * s_dir;                               // DIRECT")
    b("o_l = mx_l * s_m0 + dr_l * s_m1 + mx_l * s_m2 + mx_l * s_m3;")
    b("o_r = mx_l * s_m0 + mx_l * s_m1 + mn_l * s_m2 + mx_r * s_m3;")
    b("o_m = (o_l + o_r) * 0.5;")
    b("o_s = (o_l - o_r) * 0.5 * s_width;")
    b("o_l = o_m + o_s;")
    b("o_r = o_m - o_s;")
    b("og = s_oatt * s_ogain;")
    b(f"oc_l = {oc('o_l')};          // output amp rail (part of the character stage)")
    b(f"oc_r = {oc('o_r')};")
    b("sf_l = (o_l + (oc_l - o_l) * s_pre) * og;")
    b("sf_r = (o_r + (oc_r - o_r) * s_pre) * og;")
    b("// safety ceiling (modern): transparent below +6 dBFS, never above +12 dBFS")
    b("out1 = fixnan(sf_l / pow(1 + pow(abs(sf_l) * 0.25, 8), 0.125));")
    b("out2 = fixnan(sf_r / pow(1 + pow(abs(sf_r) * 0.25, 8), 0.125));")
    b("out3 = fixnan(20 * log10(max(mtr, 0.00001)) + 3);   // HEADROOM meter, dB")
    b("out4 = fixnan(m_s);                                  // LFO / ENV LED")
    b("out5 = fixnan(ms_disp);                              // delay time for the display (TIME, before LOOP COMP)")
    b("// v1.0.2-rc4: EXT loop send (device outputs 3/4): the regeneration tap after LOW/HIGH, unity gain")
    b("out6 = fixnan(wf_l / pow(1 + pow(abs(wf_l) * 0.25, 8), 0.125) * cal_live + cal_click);")
    b("out7 = fixnan(wf_r / pow(1 + pow(abs(wf_r) * 0.25, 8), 0.125) * cal_live + cal_click);")
    b("out8 = cal_out;                                      // rc5: CAL result for the patcher")
    b("")

    # ------------------------------------------------------------- store
    b("// ============================================================= STORE")
    stores = ["sr", "g_pre", "g_de", "g_aa", "k_aa1", "k_aa2", "k_aa3", "g_dc", "g_tone", "k_pk",
              "g_lc0", "g_lc1", "g_lc2", "g_lc6", "g_hc",
              "s_rg", "s_w1", "s_lvl", "s_pre", "s_drv", "s_tone", "s_trim", "s_fb", "s_fbs",
              "s_int", "s_bal_d", "s_bal_w", "s_so", "s_byp", "s_sat", "s_conv", "s_lcs",
              "s_lca", "s_hca", "s_lclg", "s_hclg", "s_oatt", "s_ogain", "s_width", "s_dir",
              "s_m0", "s_m1", "s_m2", "s_m3", "s_hm",
              "st_tone_l", "st_tone_r", "lph", "rnd_t", "rnd1", "rnd2", "envf", "m_s",
              "na", "nb", "xf", "xdir", "ns", "w", "hpos", "hbase",
              "st_pre_l", "st_pre_r", "st_dc_l", "st_dc_r", "ia1_l", "ia2_l", "ia1_r", "ia2_r",
              "mtr", "ph", "dac_l", "dac_r",
              "ib1_l", "ib2_l", "ib1_r", "ib2_r", "st_de_l", "st_de_r",
              "lc0_l", "lc1_l", "lc2_l", "lc6_l", "hcs_l", "lc0_r", "lc1_r", "lc2_r", "lc6_r", "hcs_r",
              "eq_b0", "eq_b1", "eq_b2", "eq_a1", "eq_a2", "eqz1_l", "eqz2_l", "eqz1_r", "eqz2_r"]
    stores += ["hst", "relk", "g_w", "gnt", "hshape"]
    stores += ["s_fbi", "s_ret"]
    stores += ["cal_st", "cal_n", "cal_m", "cal_env", "cal_res", "cal_hold", "cal_prev"]
    stores += ["s_rvo", "s_rvf", "rw", "rka", "rkb", "rla", "rlb", "dacr_l", "dacr_r"]
    stores += [f"{v}_{c}" for v in ["ib1r", "ib2r", "st_der", "eqz1r", "eqz2r", "lc0r", "lc1r", "lc2r", "lc6r", "hcsr"]
               for c in "lr"]
    for s in stores:
        b(f"h_{s} = fixnan({s});")
    b("h_lc_done = s_lclg;")
    b("h_init = 1;")
    b("h_hc_done = s_hclg;")
    b("h_xp_l = fixnan(xc_l);")
    b("h_xp_r = fixnan(xc_r);")
    b("h_fb_l = fixnan(fbn_l);")
    b("h_fb_r = fixnan(fbn_r);")

    text = "\n".join(L) + "\n" + "\n".join(body) + "\n"
    hist = sorted(set(re.findall(r"\bh_[A-Za-z0-9_]+\b", "\n".join(body))))
    decl = "\n".join(f"History {h}(0);" for h in hist)
    text = text.replace("@@HISTORIES@@", decl)
    return text


if __name__ == "__main__":
    code = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(code)
    print("wrote", os.path.relpath(OUT), len(code.splitlines()), "lines")

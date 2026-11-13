#!/usr/bin/env python3
"""
ECHOLIVITY SDD-3000 -- Max for Live device generator.

Builds dist/ECHOLIVITY SDD-3000.amxd (unfrozen audio effect, single file,
only native Max/M4L objects -- no .js, no externals, no images) from:
  * src/gen/echolivity_core.genexpr   (the tested DSP, embedded in gen~)
  * presets/factory_programs.json     (the 9 factory programs)
Also writes src/max/ECHOLIVITY_SDD-3000.maxpat (same patcher as plain JSON)
and docs/ui_preview.png (layout preview rendered from the same geometry).
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
GEN = os.path.join(ROOT, "src", "gen", "echolivity_core.genexpr")
PRESETS = os.path.join(ROOT, "presets", "factory_programs.json")
OUT_AMXD = os.path.join(ROOT, "dist", "ECHOLIVITY SDD-3000.amxd")
OUT_PAT = os.path.join(ROOT, "src", "max", "ECHOLIVITY_SDD-3000.maxpat")

DEVICE_H = 169
DEVICE_W = 1210
APPVERSION = {"major": 8, "minor": 6, "revision": 0, "architecture": "x64", "modernui": 1}

# ---------------------------------------------------------------- palette
C_FACE = [0.086, 0.086, 0.094, 1.0]
C_RAIL = [0.125, 0.125, 0.133, 1.0]
C_EAR = [0.062, 0.062, 0.066, 1.0]
C_SEP = [0.20, 0.20, 0.21, 1.0]
C_LEG = [0.90, 0.88, 0.82, 1.0]        # white legends (authentic)
C_TITLE = [0.93, 0.78, 0.30, 1.0]      # yellow section titles (authentic legend colour)
C_MOD = [0.52, 0.70, 0.86, 1.0]        # blue legends = modern enhancement
C_KNOB = [0.24, 0.24, 0.25, 1.0]
C_ARC = [0.80, 0.79, 0.74, 1.0]
C_ARC_M = [0.45, 0.66, 0.86, 1.0]
C_NEEDLE = [0.97, 0.96, 0.92, 1.0]
C_LED_ON = [1.0, 0.13, 0.08, 1.0]
C_LED_OFF = [0.20, 0.035, 0.03, 1.0]
C_GRN_ON = [0.25, 0.95, 0.30, 1.0]
C_GRN_OFF = [0.04, 0.16, 0.05, 1.0]
C_BTN = [0.17, 0.17, 0.18, 1.0]
C_DISP = [0.045, 0.010, 0.010, 1.0]


class Patch:
    def __init__(self):
        self.boxes, self.lines, self.params = [], [], {}
        self.n = 0
        self.px, self.py = 30, 260     # patching-area cursor for logic objects

    def _id(self):
        self.n += 1
        return f"obj-{self.n}"

    def _prect(self, w=80, h=22):
        r = [self.px, self.py, w, h]
        self.px += w + 12
        if self.px > 1800:
            self.px = 30
            self.py += 34
        return r

    def add(self, box, prect=None):
        box["id"] = self._id()
        box.setdefault("patching_rect", prect or self._prect())
        self.boxes.append({"box": box})
        return box["id"]

    def obj(self, text, ins, outs, outtype=None, **kw):
        b = {"maxclass": "newobj", "text": text, "numinlets": ins, "numoutlets": outs,
             "outlettype": outtype if outtype is not None else [""] * outs}
        b.update(kw)
        w = max(40, 7 * len(text) + 10)
        return self.add(b, self._prect(min(w, 420)))

    def msg(self, text):
        return self.add({"maxclass": "message", "text": text, "numinlets": 2, "numoutlets": 1,
                         "outlettype": [""]}, self._prect(max(40, 7 * len(text) + 10)))

    def link(self, a, ao, b, bi):
        self.lines.append({"patchline": {"source": [a, ao], "destination": [b, bi]}})

    # ---------------------------------------------------- presentation UI
    def panel(self, rect, color, rounded=0, border=0, bordercolor=None, varname=None, ignoreclick=1):
        b = {"maxclass": "panel", "numinlets": 1, "numoutlets": 0, "presentation": 1,
             "presentation_rect": rect, "bgfillcolor": color, "bgcolor": color, "mode": 0,
             "rounded": rounded, "border": border, "ignoreclick": ignoreclick, "background": 0}
        if bordercolor:
            b["bordercolor"] = bordercolor
        if varname:
            b["varname"] = varname
        return self.add(b, [rect[0], rect[1] + 1200, rect[2], rect[3]])

    def label(self, rect, text, color=C_LEG, size=8.5, bold=1, just=0):
        b = {"maxclass": "comment", "text": text, "numinlets": 1, "numoutlets": 0,
             "presentation": 1, "presentation_rect": rect, "textcolor": color,
             "fontname": "Arial Bold" if bold else "Arial", "fontsize": size,
             "textjustification": just, "ignoreclick": 1}
        return self.add(b, [rect[0], rect[1] + 1200, rect[2], rect[3]])

    def param_attrs(self, longname, shortname, ptype, mmin, mmax, init, enum=None, unitstyle=1,
                    exponent=1.0, invisible=0, steps=0, modmode=0, order=1):
        v = {"parameter_longname": longname, "parameter_shortname": shortname,
             "parameter_type": ptype, "parameter_mmin": float(mmin), "parameter_mmax": float(mmax),
             "parameter_initial_enable": 1, "parameter_initial": [init],
             "parameter_unitstyle": unitstyle}
        if enum is not None:
            v["parameter_enum"] = enum
        if exponent != 1.0:
            v["parameter_exponent"] = exponent
        if invisible:
            v["parameter_invisible"] = invisible
        if steps:
            v["parameter_steps"] = steps
        # v1.0.2-rc3: Live LFO/modulator "Mod" mapping requires a Modulation Mode other than
        # None (Cycling '74, Parameter Mode). 3 = Additive (None, Unipolar, Bipolar, Additive,
        # Absolute). Only continuous (Float) dials use it; Enum parameters cannot be modulated.
        if modmode:
            v["parameter_modmode"] = modmode
        # v1.0.2-rc3 (D-1): recall order. Lower numbers are restored first (Cycling '74,
        # Parameter Mode / Initial Value). Program is order 0 so that its recall of a slot
        # happens BEFORE the panel and the slots are restored from a preset, which then win.
        if order:
            v["parameter_order"] = order
        return {"valueof": v}

    def register(self, oid, longname, shortname):
        if any(v[0] == longname for v in self.params.values()):
            raise ValueError("duplicate parameter name " + longname)
        self.params[oid] = [longname, shortname, 0]


# =================================================================== controls
# key: (gen param, longname, shortname, kind, range/enum, init, rect, modern, extra)
# kinds: dial, tab, text (toggle), menu
def controls():
    C = []

    def d(key, gp, ln, sn, lo, hi, init, rect, modern=False, unit=1, exp=1.0, scale=None):
        C.append(dict(key=key, gp=gp, ln=ln, sn=sn, kind="dial", lo=lo, hi=hi, init=init, rect=rect,
                      modern=modern, unit=unit, exp=exp, scale=scale))

    def e(key, gp, ln, sn, kind, enum, init, rect, modern=False, lines=None, text=None):
        C.append(dict(key=key, gp=gp, ln=ln, sn=sn, kind=kind, enum=enum, init=init, rect=rect,
                      modern=modern, lines=lines, text=text))

    # A INPUT
    e("in_range", "p_in_range", "Input Attenuator", "IN ATT", "tab", ["-30", "-10", "+4"], 2,
      [22, 22, 30, 48], lines=3)
    d("in_level", "p_in_level", "Input Level", "LEVEL", 0, 10, 5, [56, 17, 44, 52])
    e("pre_on", "p_pre_on", "Preamp Character", "PRE", "text", ["off", "on"], 1, [22, 98, 30, 14],
      text=("PRE", "PRE"))
    e("pre_comp", "p_pre_comp", "Preamp Auto Comp", "COMP", "text", ["off", "on"], 1, [22, 116, 30, 14],
      modern=True, text=("COMP", "COMP"))
    d("drive", "p_drive", "Preamp Drive", "DRIVE", 0, 24, 0, [54, 92, 32, 50], unit=4)
    d("tone", "p_tone", "Preamp Tone", "TONE", -100, 100, 0, [86, 92, 32, 50], unit=5, scale=0.01)
    d("pre_trim", "p_pre_trim", "Preamp Trim", "TRIM", -24, 24, 0, [118, 92, 32, 50], unit=4)
    # B DELAY
    d("time_ms", "p_time_ms", "Delay Time", "TIME", 0, 1023, 380, [318, 14, 58, 66], unit=2, exp=2.2)
    e("time_mode", "p_time_mode", "Time Mode", "T MODE", "tab", ["1ms", "CONT"], 0, [158, 98, 64, 15],
      modern=True, lines=1)
    e("time_glide", "p_time_glide", "Time Change", "CHANGE", "tab", ["XFADE", "GLIDE"], 0,
      [158, 118, 64, 15], modern=True, lines=1)
    e("sync", "p_sync", "Tempo Sync", "SYNC", "text", ["off", "on"], 0, [228, 98, 44, 15],
      modern=True, text=("SYNC", "SYNC"))
    e("division", "p_division", "Sync Division", "DIV", "menu",
      # rc5: musician labels (T = triplet, D = dotted); same values and indices as before.
      # 1/16T and 1/32T are appended so existing Sets and programs keep their division.
      ["1/32", "1/16", "1/8T", "1/8", "1/4T", "1/8D", "1/4", "1/2T", "1/4D", "1/2", "1/1", "1/16T", "1/32T"], 8,
      [228, 118, 52, 15], modern=True)
    # C MODULATION
    e("waveform", "p_waveform", "Mod Waveform", "WAVE", "tab", ["TRI", "SQR", "RND", "ENV"], 0,
      [410, 22, 36, 66], lines=4)
    d("intensity", "p_intensity", "Mod Intensity", "INTENS", 0, 10, 0, [450, 17, 50, 56])
    d("frequency", "p_frequency", "Mod Frequency", "FREQ", 0, 10, 3, [502, 17, 50, 56])
    d("env_sens", "p_env_sens", "Env Sensitivity", "ENV SENS", -24, 24, 0, [450, 96, 46, 50],
      modern=True, unit=4)
    d("env_rel", "p_env_rel", "Env Release", "ENV REL", 20, 5000, 1440, [500, 96, 46, 50],
      modern=True, unit=2, exp=3.0)
    # D REGENERATION
    d("feedback", "p_feedback", "Feedback", "FEEDBK", 0, 10, 3, [570, 14, 58, 66])
    e("fb_inv", "p_fb_inv", "Regen Invert", "INV", "text", ["off", "on"], 0, [632, 22, 34, 16],
      text=("INV", "INV"))
    e("hold", "p_hold", "Hold", "HOLD", "text", ["off", "on"], 0, [632, 44, 34, 16],
      text=("HOLD", "HOLD"))
    e("lowcut", "p_lowcut", "Low Cut", "LOW", "tab", ["FLAT", "125", "250", "500"], 0,
      [672, 22, 40, 66], lines=4)
    e("highcut", "p_highcut", "High Cut", "HIGH", "tab", ["FLAT", "8K", "4K", "2K"], 0,
      [716, 22, 40, 66], lines=4)
    e("loop_sat", "p_loop_sat", "Loop Saturation", "SAT", "tab", ["HARD", "SOFT"], 0,
      [570, 112, 70, 15], modern=True, lines=1)
    e("lc_slope", "p_lc_slope", "Low Cut Slope", "SLOPE", "tab", ["3dB", "6dB"], 0,
      [672, 112, 84, 15], modern=True, lines=1)
    # v1.0.2-rc4: external regeneration loop (device outputs 3/4 -> another track -> inputs 3/4)
    e("fb_route", "p_fb_route", "FB Route", "FB ROUTE", "tab", ["INT", "EXT", "BOTH"], 0,
      [570, 142, 78, 15], modern=True, lines=1)
    C.append(dict(key="ret_level", gp="p_return", ln="Ext Return", sn="RETURN", kind="numbox", lo=0, hi=10,
                  init=5, rect=[652, 142, 34, 15], modern=True, unit=1, exp=1.0, scale=None))
    # rc5: LOOP COMP (ms, set by CAL or by hand); not modulatable
    C.append(dict(key="loop_comp", gp="p_loop_comp", ln="Loop Comp", sn="COMP", kind="numbox", lo=0, hi=250,
                  init=0, rect=[690, 142, 38, 15], modern=True, unit=1, exp=1.0, scale=None, mod=False))
    # REVERSE (modern, owner request): not stored in programs, like the other routing/modern extras
    e("reverse", "p_reverse", "Reverse", "REVERSE", "menu", ["OFF", "REV", "ALT", "ALT R"], 0,
      [570, 95, 62, 14], modern=True)
    # E EFFECT / OUTPUT
    d("balance", "p_balance", "Balance", "BALANCE", 0, 10, 5, [776, 14, 58, 66])
    e("out_inv", "p_out_inv", "Output Invert", "OUT INV", "text", ["off", "on"], 0, [838, 22, 42, 16],
      text=("INV", "INV"))
    e("bypass", "p_bypass", "Bypass", "BYPASS", "text", ["off", "on"], 0, [838, 44, 42, 16],
      text=("BYPASS", "BYPASS"))
    e("out_range", "p_out_range", "Output Attenuator", "OUT ATT", "tab", ["-20", "-10", "+4"], 2,
      [886, 22, 30, 48], lines=3)
    e("out_mode", "p_out_mode", "Output Mode", "OUT MODE", "menu",
      ["MONO", "STEREO A", "STEREO B", "TRUE ST"], 0, [922, 22, 78, 16])
    d("width", "p_width", "Stereo Width", "WIDTH", 0, 200, 100, [776, 96, 44, 50], modern=True,
      unit=5, scale=0.01)
    d("out_gain", "p_out_gain", "Output Gain", "GAIN", -24, 12, 0, [822, 96, 44, 50], modern=True,
      unit=4)
    e("wet_only", "p_wet_only", "Wet Only", "WET", "text", ["off", "on"], 0, [870, 100, 58, 15],
      modern=True, text=("WET ONLY", "WET ONLY"))
    e("converter", "p_converter", "Converter", "CONV", "tab", ["13-BIT", "CLEAN"], 0,
      [870, 120, 130, 15], modern=True, lines=1)
    return C


# program-memory fields (hardware stores delay time + regeneration + modulation + effect)
FIELDS = ["time_ms", "feedback", "fb_inv", "lowcut", "highcut", "waveform", "intensity",
          "frequency", "balance", "time_mode", "sync", "division"]

# 7-segment masks (bit0=a ... bit6=g), digits 0-9, 10=blank, 11='-'
SEG = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F, 0x00, 0x40]
SEG_WORD = [sum(((SEG[d] >> k) & 1) << d for d in range(12)) for k in range(7)]


def seg_rects(x, y, W=22, H=40, T=4):
    h2 = H / 2
    return [
        [x + T, y, W - 2 * T, T],                         # a
        [x + W - T, y + T, T, h2 - 1.5 * T],              # b
        [x + W - T, y + h2 + 0.5 * T, T, h2 - 1.5 * T],   # c
        [x + T, y + H - T, W - 2 * T, T],                 # d
        [x, y + h2 + 0.5 * T, T, h2 - 1.5 * T],           # e
        [x, y + T, T, h2 - 1.5 * T],                      # f
        [x + T, y + h2 - T / 2, W - 2 * T, T],            # g
    ]


def build():
    P = Patch()
    preview = {"panels": [], "labels": [], "controls": []}
    code = open(GEN).read()
    progs = json.load(open(PRESETS))

    # ------------------------------------------------------------ faceplate
    def ppanel(rect, color, **kw):
        preview["panels"].append((rect, color, kw.get("rounded", 0)))
        return P.panel(rect, color, **kw)

    def plabel(rect, text, color=C_LEG, size=8.5, bold=1, just=0):
        preview["labels"].append((rect, text, color, size, just))
        return P.label(rect, text, color, size, bold, just)

    ppanel([0, 0, DEVICE_W, DEVICE_H], C_FACE)
    ppanel([0, 0, DEVICE_W, 3], C_RAIL)
    ppanel([0, DEVICE_H - 3, DEVICE_W, 3], C_RAIL)
    for x in (0, DEVICE_W - 16):
        ppanel([x, 0, 16, DEVICE_H], C_EAR)
        for y in (16, DEVICE_H - 26):
            ppanel([x + 4, y, 8, 8], [0.16, 0.16, 0.17, 1.0], rounded=8)
    seps = [152, 404, 564, 768, 1006]
    for x in seps:
        ppanel([x, 8, 1, DEVICE_H - 16], C_SEP)
    titles = [(20, "INPUT"), (156, "DELAY"), (408, "MODULATION"), (568, "REGENERATION"),
              (772, "EFFECT / OUTPUT"), (1010, "PROGRAM")]
    for x, t in titles:
        plabel([x, 4, 150, 14], t, C_TITLE, 9.5)
    # modern-row hairlines + tags
    for x0, x1 in ((20, 150), (156, 402), (408, 562), (568, 766), (772, 1004)):
        ppanel([x0, 90, x1 - x0, 1], [0.15, 0.15, 0.16, 1.0])
    plabel([20, 142, 140, 12], "PREAMP CHARACTER", C_LEG, 7.5)
    plabel([408, 146, 150, 12], "ENVELOPE  (EXT)", C_MOD, 7.5)
    plabel([158, 136, 150, 12], "TIME / SYNC  (EXT)", C_MOD, 7.5)
    plabel([672, 128, 90, 12], "LOW CUT SLOPE", C_MOD, 7)
    plabel([570, 128, 90, 12], "LOOP SAT", C_MOD, 7)
    plabel([636, 97, 36, 11], "REVERSE", C_MOD, 6.5)
    plabel([570, 157, 80, 11], "FB ROUTE (I/O 3-4)", C_MOD, 6.5)
    plabel([652, 157, 36, 11], "RETURN", C_MOD, 6.5)
    plabel([690, 157, 40, 11], "COMP ms", C_MOD, 6.5)
    plabel([732, 157, 26, 11], "CAL", C_MOD, 6.5)
    plabel([870, 138, 134, 12], "CONVERTER  (EXT)", C_MOD, 7)
    plabel([672, 89, 40, 12], "LOW", C_LEG, 7.5, 1, 1)
    plabel([716, 89, 40, 12], "HIGH", C_LEG, 7.5, 1, 1)
    plabel([22, 71, 34, 12], "ATT", C_LEG, 7.5, 1, 1)
    plabel([886, 71, 30, 12], "ATT", C_LEG, 7.5, 1, 1)
    plabel([410, 89, 36, 12], "WAVE", C_LEG, 7.5, 1, 1)

    # headroom meter
    meter_th = [3, 0, -5, -10, -15, -20]
    meter_ids = []
    for i, th in enumerate(meter_th):
        y = 22 + i * 8
        on, off = (C_LED_ON, C_LED_OFF) if th > 0 else (C_GRN_ON, C_GRN_OFF)
        meter_ids.append((ppanel([106, y, 7, 5], off, rounded=1), on, off, th))
        plabel([115, y - 4, 32, 11], f"{th:+d}" if th else "0", C_LEG, 6.5, 0)
    plabel([100, 72, 50, 11], "HEADROOM", C_LEG, 6.5)

    # LED display window
    ppanel([156, 20, 158, 62], C_DISP, rounded=3, border=1, bordercolor=[0.25, 0.05, 0.05, 1.0])
    digit_x = [163, 205, 232, 259, 286]
    digit_segs = []
    for dx in digit_x:
        ids = [ppanel(r, C_LED_OFF, rounded=1) for r in seg_rects(dx, 26)]
        digit_segs.append(ids)
    dp_id = ppanel([188, 62, 4, 4], C_LED_OFF, rounded=2)
    plabel([158, 82, 50, 12], "PROG", C_LEG, 7)
    plabel([204, 82, 110, 12], "DELAY TIME  ms", C_LEG, 7)
    lfo_led = ppanel([546, 20, 6, 6], C_LED_OFF, rounded=3)

    # brand block
    plabel([1010, 112, 190, 18], "ECHOLIVITY", C_LEG, 14)
    plabel([1010, 130, 190, 12], "SDD-3000   DIGITAL DELAY", C_TITLE, 8)
    plabel([1010, 143, 196, 11], "independent homage  -  not a Korg product", [0.45, 0.45, 0.45, 1], 6.5, 0)
    plabel([1010, 154, 100, 10], "■ original", C_LEG, 6.5, 0)
    plabel([1060, 154, 140, 10], "■ modern / EXT", C_MOD, 6.5, 0)

    # ------------------------------------------------------------- audio
    gen_patch = {
        "fileversion": 1, "appversion": APPVERSION, "classnamespace": "dsp.gen",
        "rect": [100, 100, 900, 700], "bglocked": 0, "openinpresentation": 0,
        "default_fontsize": 12.0, "default_fontface": 0, "default_fontname": "Arial",
        "gridonopen": 1, "gridsize": [15.0, 15.0], "gridsnaponopen": 1, "objectsnaponopen": 1,
        "statusbarvisible": 2, "toolbarvisible": 1, "boxanimatetime": 200, "enablehscroll": 1,
        "enablevscroll": 1, "devicewidth": 0.0, "description": "", "digest": "", "tags": "",
        "style": "", "subpatcher_template": "",
        "boxes": [
            {"box": {"id": "obj-1", "maxclass": "newobj", "text": "in 1", "numinlets": 0,
                     "numoutlets": 1, "outlettype": [""], "patching_rect": [20, 15, 30, 22]}},
            {"box": {"id": "obj-2", "maxclass": "newobj", "text": "in 2", "numinlets": 0,
                     "numoutlets": 1, "outlettype": [""], "patching_rect": [400, 15, 30, 22]}},
            {"box": {"id": "obj-3", "maxclass": "codebox", "code": code, "fontface": 0,
                     "fontname": "<Monospaced>", "fontsize": 12.0, "numinlets": 4, "numoutlets": 8,
                     "outlettype": [""] * 8, "patching_rect": [20, 50, 760, 560]}},
            # v1.0.2-rc4: EXT regeneration loop return (device inputs 3/4)
            {"box": {"id": "obj-20", "maxclass": "newobj", "text": "in 3", "numinlets": 0,
                     "numoutlets": 1, "outlettype": [""], "patching_rect": [560, 15, 30, 22]}},
            {"box": {"id": "obj-21", "maxclass": "newobj", "text": "in 4", "numinlets": 0,
                     "numoutlets": 1, "outlettype": [""], "patching_rect": [740, 15, 30, 22]}},
        ] + [{"box": {"id": f"obj-{4 + k}", "maxclass": "newobj", "text": f"out {k + 1}",
                      "numinlets": 1, "numoutlets": 0, "patching_rect": [20 + 110 * k, 630, 40, 22]}}
             for k in range(8)],
        "lines": [{"patchline": {"source": ["obj-1", 0], "destination": ["obj-3", 0]}},
                  {"patchline": {"source": ["obj-2", 0], "destination": ["obj-3", 1]}},
                  {"patchline": {"source": ["obj-20", 0], "destination": ["obj-3", 2]}},
                  {"patchline": {"source": ["obj-21", 0], "destination": ["obj-3", 3]}}] +
                 [{"patchline": {"source": ["obj-3", k], "destination": [f"obj-{4 + k}", 0]}}
                  for k in range(8)],
    }
    # v1.0.2-rc4: 4 in / 4 out. Device inputs 3/4 = EXT loop return, outputs 3/4 = EXT loop send.
    # Live exposes extra plugin~/plugout~ channels as routable stereo pairs (Cycling '74, Audio Routes).
    plugin = P.add({"maxclass": "newobj", "text": "plugin~ 1 2 3 4", "numinlets": 1, "numoutlets": 4,
                    "outlettype": ["signal"] * 4}, [30, 40, 120, 22])
    gen = P.add({"maxclass": "newobj", "text": "gen~", "numinlets": 4, "numoutlets": 8,
                 "outlettype": ["signal"] * 8, "patcher": gen_patch}, [30, 120, 500, 22])
    plugout = P.add({"maxclass": "newobj", "text": "plugout~ 1 2 3 4", "numinlets": 4, "numoutlets": 4,
                     "outlettype": ["signal"] * 4}, [30, 200, 120, 22])
    P.link(plugin, 0, gen, 0)
    P.link(plugin, 1, gen, 1)
    P.link(plugin, 2, gen, 2)
    P.link(plugin, 3, gen, 3)
    P.link(gen, 0, plugout, 0)
    P.link(gen, 1, plugout, 1)
    P.link(gen, 5, plugout, 2)
    P.link(gen, 6, plugout, 3)

    # ----------------------------------------------------------- controls
    ctrl_ids = {}
    for c in controls():
        rect = c["rect"]
        legend = C_MOD if c["modern"] else C_LEG
        if c["kind"] == "dial":
            sv = P.param_attrs(c["ln"], c["sn"], 0, c["lo"], c["hi"], c["init"], unitstyle=c["unit"],
                               exponent=c["exp"], modmode=3)
            b = {"maxclass": "live.dial", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "float"],
                 "parameter_enable": 1, "presentation": 1, "presentation_rect": rect,
                 "saved_attribute_attributes": sv, "varname": c["key"], "showname": 1, "shownumber": 1,
                 "fontname": "Arial Bold", "fontsize": 8.0 if rect[2] < 50 else 9.0,
                 "textcolor": legend, "dialcolor": C_KNOB, "activedialcolor": C_ARC_M if c["modern"] else C_ARC,
                 "needlecolor": C_NEEDLE, "activeneedlecolor": C_NEEDLE, "fgdialcolor": C_KNOB,
                 "activefgdialcolor": C_ARC_M if c["modern"] else C_ARC, "triangle": 1,
                 "tricolor": [0.5, 0.5, 0.5, 1], "focusbordercolor": C_TITLE, "bordercolor": [0, 0, 0, 0]}
        elif c["kind"] == "numbox":
            # v1.0.2-rc4: continuous value in a compact box (Float, modulatable like the dials)
            sv = P.param_attrs(c["ln"], c["sn"], 0, c["lo"], c["hi"], c["init"], unitstyle=c["unit"],
                               modmode=3 if c.get("mod", True) else 0)
            b = {"maxclass": "live.numbox", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "float"],
                 "parameter_enable": 1, "presentation": 1, "presentation_rect": rect,
                 "saved_attribute_attributes": sv, "varname": c["key"], "fontname": "Arial Bold",
                 "fontsize": 8.0, "textcolor": legend, "activeslidercolor": C_ARC_M,
                 "bordercolor": [0.30, 0.30, 0.31, 1.0], "focusbordercolor": C_TITLE}
        else:
            enum = c["enum"]
            sv = P.param_attrs(c["ln"], c["sn"], 2, 0, len(enum) - 1, c["init"], enum=enum, unitstyle=10)
            common = {"parameter_enable": 1, "presentation": 1, "presentation_rect": rect,
                      "saved_attribute_attributes": sv, "varname": c["key"],
                      "fontname": "Arial Bold", "fontsize": 7.5}
            if c["kind"] == "tab":
                b = {"maxclass": "live.tab", "numinlets": 1, "numoutlets": 3,
                     "outlettype": ["", "", "float"], "num_lines_patching": c["lines"],
                     "num_lines_presentation": c["lines"], "spacing_x": 1.0, "spacing_y": 1.0,
                     "bgcolor": C_BTN, "activebgcolor": C_BTN,
                     "bgoncolor": C_ARC_M if c["modern"] else [0.86, 0.20, 0.12, 1.0],
                     "activebgoncolor": C_ARC_M if c["modern"] else [0.86, 0.20, 0.12, 1.0],
                     "textcolor": legend, "textoncolor": [0.05, 0.05, 0.05, 1.0],
                     "bordercolor": [0.30, 0.30, 0.31, 1.0], "focusbordercolor": C_TITLE}
            elif c["kind"] == "text":
                b = {"maxclass": "live.text", "numinlets": 1, "numoutlets": 2, "outlettype": ["", ""],
                     "mode": 1, "text": c["text"][0], "texton": c["text"][1],
                     "bgcolor": C_BTN, "activebgcolor": C_BTN,
                     "bgoncolor": C_ARC_M if c["modern"] else C_LED_ON,
                     "activebgoncolor": C_ARC_M if c["modern"] else C_LED_ON,
                     "textcolor": legend, "activetextcolor": legend,
                     "textoncolor": [0.05, 0.05, 0.05, 1.0], "activetextoncolor": [0.05, 0.05, 0.05, 1.0],
                     "bordercolor": [0.30, 0.30, 0.31, 1.0], "focusbordercolor": C_TITLE, "rounded": 2.0}
            else:
                b = {"maxclass": "live.menu", "numinlets": 1, "numoutlets": 3,
                     "outlettype": ["", "", "float"], "bgcolor": C_BTN, "activebgcolor": C_BTN,
                     "textcolor": legend, "activetextcolor": legend, "tricolor": legend,
                     "bordercolor": [0.30, 0.30, 0.31, 1.0], "focusbordercolor": C_TITLE}
            b.update(common)
        oid = P.add(b, [600 + 110 * (len(ctrl_ids) % 12), 40 + 60 * (len(ctrl_ids) // 12), rect[2], rect[3]])
        P.register(oid, c["ln"], c["sn"])
        ctrl_ids[c["key"]] = (oid, c)
        preview["controls"].append((c, legend))
        # -> gen~
        src = oid
        if c.get("scale"):
            sc = P.obj(f"* {c['scale']}", 2, 1)
            P.link(oid, 0, sc, 0)
            src = sc
        pp = P.obj(f"prepend {c['gp']}", 2, 1)
        P.link(src, 0, pp, 0)
        P.link(pp, 0, gen, 0)

    # -------------------------------------------------- tempo (host sync)
    td = P.obj("live.thisdevice", 1, 3, ["bang", "int", "int"])
    t_init = P.obj("t b b b b b", 1, 5)
    P.link(td, 0, t_init, 0)
    m_path = P.msg("path live_set")
    m_prop = P.msg("property tempo")
    lpath = P.obj("live.path", 2, 3, ["", "", ""])
    lobs = P.obj("live.observer", 2, 2, ["", ""])
    pt = P.obj("prepend p_tempo", 2, 1)
    P.link(t_init, 4, m_path, 0)
    P.link(m_path, 0, lpath, 0)
    P.link(lpath, 0, lobs, 1)
    P.link(t_init, 4, m_prop, 0)
    P.link(m_prop, 0, lobs, 0)
    P.link(lobs, 0, pt, 0)
    P.link(pt, 0, gen, 0)

    # ------------------------------------------------- program memory
    # hidden "stored only" parameters: slot 0 = manual snapshot, slots 1-9 = programs
    slot_ids = [[None] * len(FIELDS) for _ in range(10)]
    for k in range(10):
        vals = progs["manual"] if k == 0 else progs["programs"][k - 1]["values"]
        for j, f in enumerate(FIELDS):
            oid_c, c = ctrl_ids[f]
            if c["kind"] == "dial":
                lo, hi = c["lo"], c["hi"]
            else:
                lo, hi = 0, len(c["enum"]) - 1
            name = f"Mem{k} {c['ln']}" if k else f"Manual {c['ln']}"
            sv = P.param_attrs(name, f"M{k}{j}", 0, lo, hi, float(vals[f]), unitstyle=1, invisible=1)
            oid = P.add({"maxclass": "live.numbox", "numinlets": 1, "numoutlets": 2,
                         "outlettype": ["", "float"], "parameter_enable": 1,
                         "saved_attribute_attributes": sv, "varname": f"mem_{k}_{f}"},
                        [30 + 64 * j, 1500 + 26 * k, 56, 15])
            P.register(oid, name, f"M{k}{j}")
            slot_ids[k][j] = oid

    # per field: value cache, write gate, recall gate
    r_wslot = P.obj("r ---wslot", 0, 1)
    r_wbang = P.obj("r ---wbang", 0, 1)
    r_ropen = P.obj("r ---ropen", 0, 1)
    s_edit = P.obj("s ---edit", 1, 0)
    for j, f in enumerate(FIELDS):
        cid, c = ctrl_ids[f]
        cache = P.obj("f", 2, 1)
        P.link(cid, 0, cache, 1)
        tb = P.obj("t b", 1, 1)
        P.link(cid, 0, tb, 0)
        P.link(tb, 0, s_edit, 0)
        P.link(r_wbang, 0, cache, 0)
        ps = P.obj("prepend set", 2, 1)
        P.link(cache, 0, ps, 0)
        wg = P.obj("gate 10", 2, 10)
        P.link(r_wslot, 0, wg, 0)
        P.link(ps, 0, wg, 1)
        rg = P.obj("gate 1", 2, 1)
        P.link(r_ropen, 0, rg, 0)
        P.link(rg, 0, cid, 0)
        for k in range(10):
            P.link(wg, k, slot_ids[k][j], 0)
            P.link(slot_ids[k][j], 0, rg, 1)
    # recall: open gates, bang slot k, close gates
    r_recall = P.obj("r ---recall", 0, 1)
    t_rec = P.obj("t b b i b", 1, 4)
    P.link(r_recall, 0, t_rec, 0)
    m1 = P.msg("1")
    m0 = P.msg("0")
    s_ropen1 = P.obj("s ---ropen", 1, 0)
    P.link(t_rec, 3, m1, 0)
    P.link(m1, 0, s_ropen1, 0)
    P.link(t_rec, 0, m0, 0)
    P.link(m0, 0, s_ropen1, 0)
    plus1 = P.obj("+ 1", 2, 1)
    P.link(t_rec, 2, plus1, 0)
    bg = P.obj("gate 10", 2, 10)
    P.link(plus1, 0, bg, 0)
    P.link(t_rec, 1, bg, 1)
    for k in range(10):
        tk = P.obj("t " + " ".join(["b"] * len(FIELDS)), 1, len(FIELDS))
        P.link(bg, k, tk, 0)
        for j in range(len(FIELDS)):
            P.link(tk, j, slot_ids[k][j], 0)
    # write: slot select then bang caches
    r_write = P.obj("r ---write", 0, 1)
    t_wr = P.obj("t b i", 1, 2)
    P.link(r_write, 0, t_wr, 0)
    plus1w = P.obj("+ 1", 2, 1)
    P.link(t_wr, 1, plus1w, 0)
    s_wslot = P.obj("s ---wslot", 1, 0)
    P.link(plus1w, 0, s_wslot, 0)
    s_wbang = P.obj("s ---wbang", 1, 0)
    P.link(t_wr, 0, s_wbang, 0)

    # program selector + logic
    prog = P.add({"maxclass": "live.tab", "numinlets": 1, "numoutlets": 3,
                  "outlettype": ["", "", "float"], "parameter_enable": 1, "presentation": 1,
                  "presentation_rect": [1010, 22, 150, 36], "num_lines_patching": 2,
                  "num_lines_presentation": 2, "spacing_x": 1.0, "spacing_y": 1.0,
                  "saved_attribute_attributes": P.param_attrs(
                      "Program", "PROG", 2, 0, 9, 0, enum=["M"] + [str(i) for i in range(1, 10)], unitstyle=10,
                      order=0),
                  "varname": "program", "fontname": "Arial Bold", "fontsize": 8.5,
                  "bgcolor": C_BTN, "activebgcolor": C_BTN, "bgoncolor": [0.86, 0.20, 0.12, 1.0],
                  "activebgoncolor": [0.86, 0.20, 0.12, 1.0], "textcolor": C_LEG,
                  "textoncolor": [0.05, 0.05, 0.05, 1], "bordercolor": [0.30, 0.30, 0.31, 1.0],
                  "focusbordercolor": C_TITLE}, [30, 1800, 150, 36])
    P.register(prog, "Program", "PROG")
    preview["controls"].append(({"kind": "tab", "rect": [1010, 22, 150, 36],
                                 "enum": ["M"] + [str(i) for i in range(1, 10)], "lines": 2, "sn": "PROG",
                                 "init": 0, "modern": False}, C_LEG))

    def button(ln, sn, rect, txt, modern=False):
        b = {"maxclass": "live.text", "numinlets": 1, "numoutlets": 2, "outlettype": ["", ""],
             "parameter_enable": 1, "presentation": 1, "presentation_rect": rect, "mode": 0,
             "text": txt, "texton": txt, "saved_attribute_attributes":
                 P.param_attrs(ln, sn, 2, 0, 1, 0, enum=["off", "on"], unitstyle=10),
             "fontname": "Arial Bold", "fontsize": 8.0, "bgcolor": C_BTN, "activebgcolor": C_BTN,
             "bgoncolor": C_LED_ON, "activebgoncolor": C_LED_ON, "textcolor": C_LEG,
             "activetextcolor": C_LEG, "bordercolor": [0.30, 0.30, 0.31, 1.0], "rounded": 2.0}
        oid = P.add(b, [200 + 120 * len(preview["controls"]) % 1200, 1850, rect[2], rect[3]])
        P.register(oid, ln, sn)
        preview["controls"].append(({"kind": "text", "rect": rect, "text": (txt, txt), "sn": sn,
                                     "init": 0, "modern": modern}, C_LEG))
        # accept both 'bang' and '1' as a press
        rb = P.obj("route bang", 2, 2)
        P.link(oid, 0, rb, 0)
        s1 = P.obj("sel 1", 2, 2)
        P.link(rb, 1, s1, 0)
        press = P.obj("t b", 1, 1)
        P.link(rb, 0, press, 0)
        P.link(s1, 0, press, 0)
        return press

    up = button("Program Up", "PROG+", [1164, 22, 30, 17], "▲")
    dn = button("Program Down", "PROG-", [1164, 41, 30, 17], "▼")
    wr = button("Write", "WRITE", [1010, 66, 56, 18], "WRITE")
    # rc5: CAL -- measure the EXT loop round trip; gen~ reports it on out8 and it is written into LOOP COMP
    cal = button("Loop Cal", "CAL", [732, 142, 26, 15], "CAL", modern=True)
    cal_t = P.obj("t b b", 1, 2)
    P.link(cal, 0, cal_t, 0)
    cal_on = P.msg("p_cal 1")
    P.link(cal_t, 1, cal_on, 0)
    P.link(cal_on, 0, gen, 0)
    cal_dl = P.obj("delay 30", 2, 1)
    P.link(cal_t, 0, cal_dl, 0)
    cal_off = P.msg("p_cal 0")
    P.link(cal_dl, 0, cal_off, 0)
    P.link(cal_off, 0, gen, 0)
    cal_snap = P.obj("snapshot~ 20", 2, 1, ["float"])
    P.link(gen, 7, cal_snap, 0)
    cal_chg = P.obj("change", 1, 3, ["", "int", "int"])
    P.link(cal_snap, 0, cal_chg, 0)
    cal_ok = P.obj("if $f1 >= 0. then $f1", 1, 1)
    P.link(cal_chg, 0, cal_ok, 0)
    P.link(cal_ok, 0, ctrl_ids["loop_comp"][0], 0)
    to = P.add({"maxclass": "live.numbox", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "float"],
                "parameter_enable": 1, "presentation": 1, "presentation_rect": [1094, 66, 34, 18],
                "saved_attribute_attributes": P.param_attrs("Write Target", "TO", 1, 1, 9, 1, unitstyle=0),
                "varname": "write_to", "fontname": "Arial Bold", "fontsize": 9.0,
                "textcolor": C_LEG, "activebgcolor": C_BTN, "bgcolor": C_BTN,
                "bordercolor": [0.30, 0.30, 0.31, 1.0]}, [400, 1900, 34, 18])
    P.register(to, "Write Target", "TO")
    plabel([1070, 69, 24, 12], "TO", C_LEG, 7.5)
    preview["controls"].append(({"kind": "numbox", "rect": [1094, 66, 34, 18], "init": 1,
                                 "modern": False, "sn": "TO"}, C_LEG))
    # rc6: FB ROUTE chooser - pick the regeneration SEND destination (device outputs 3/4) and RETURN
    # source (device inputs 3/4) from the panel. A v8.codebox (src/max/fb_route_chooser.js, Live 12.2+ /
    # Max 9) lists the DeviceIO routing types/channels Live offers and applies the choice; the routing is
    # Live's own state, so the menus are plain umenus, not Live parameters (their contents change with the
    # Set). Replaces the WRITE help text (now in the manual).
    route_js = open(os.path.join(ROOT, "src", "max", "fb_route_chooser.js")).read()
    v8 = P.add({"maxclass": "v8.codebox", "code": route_js, "filename": "none", "numinlets": 1,
                "numoutlets": 4, "outlettype": ["", "", "", ""], "fontface": 0, "fontname": "<Monospaced>",
                "fontsize": 10.0}, [1300, 300, 600, 400])
    P.link(td, 0, v8, 0)
    route_rows = (("SEND", 87, ("sendtype", "sendchan"),
                   ("Regeneration SEND (device outputs 3/4): destination track",
                    "Regeneration SEND: destination channel")),
                  ("RTN", 99, ("rettype", "retchan"),
                   ("Regeneration RETURN (device inputs 3/4): source track",
                    "Regeneration RETURN: tap point on the source track")))
    k = 0
    for lab, y, cmds, hints in route_rows:
        plabel([1010, y, 28, 11], lab, C_MOD, 6.5)
        for (x, w), cmd, hint in zip(((1036, 102), (1140, 54)), cmds, hints):
            um = P.add({"maxclass": "umenu", "numinlets": 1, "numoutlets": 3, "outlettype": ["int", "", ""],
                        "items": ["-"], "parameter_enable": 0, "presentation": 1,
                        "presentation_rect": [x, y, w, 11], "fontname": "Arial Bold", "fontsize": 6.5,
                        "bgcolor": C_BTN, "textcolor": C_LEG, "color": C_MOD, "arrow": 1,
                        "annotation": hint, "hint": hint, "varname": f"fbroute_{cmd}"},
                       [1300 + 140 * k, 760, w, 20])
            P.link(v8, k, um, 0)
            pre = P.obj(f"prepend {cmd}", 1, 1)
            P.link(um, 0, pre, 0)
            P.link(pre, 0, v8, 0)
            preview["controls"].append(({"kind": "menu", "rect": [x, y, w, 11], "enum": ["-"], "init": 0,
                                         "sn": cmd}, C_LEG))
            k += 1

    # tab -> [t i i]: first the logic (with OLD prev), then prev/pcur/display update
    t_p = P.obj("t i i", 1, 2)
    P.link(prog, 0, t_p, 0)
    g_logic = P.obj("gate 1", 2, 1)              # closed until the device has initialised
    P.link(t_p, 1, g_logic, 1)
    ex_leave = P.obj("expr ($i1 != 0) && ($i2 == 0)", 2, 1)
    i_cur = P.obj("i", 2, 1)
    P.link(t_p, 0, ex_leave, 1)
    P.link(t_p, 0, i_cur, 1)
    t_l = P.obj("t i i i", 1, 3)
    P.link(g_logic, 0, t_l, 0)
    # (a) leaving manual -> snapshot the panel into slot 0
    P.link(t_l, 2, ex_leave, 0)
    sel_leave = P.obj("sel 1", 2, 2)
    P.link(ex_leave, 0, sel_leave, 0)
    m_slot0 = P.msg("0")
    s_write = P.obj("s ---write", 1, 0)
    P.link(sel_leave, 0, m_slot0, 0)
    P.link(m_slot0, 0, s_write, 0)
    # (b) recall the selected slot (0 = manual snapshot)
    s_recall = P.obj("s ---recall", 1, 0)
    P.link(t_l, 1, s_recall, 0)
    # (c) clear the edit flag; TO follows a stored program
    s_editclr = P.obj("s ---editclr", 1, 0)
    t_c = P.obj("t i b", 1, 2)
    P.link(t_l, 0, t_c, 0)
    P.link(t_c, 1, s_editclr, 0)
    sel0 = P.obj("sel 0", 2, 2)
    P.link(t_c, 0, sel0, 0)
    P.link(sel0, 1, to, 0)
    # edit flag only meaningful while a stored program is active
    gt0 = P.obj("> 0", 2, 1)
    P.link(t_p, 0, gt0, 0)
    g_edit = P.obj("gate 1", 2, 1)
    P.link(gt0, 0, g_edit, 0)
    r_edit = P.obj("r ---edit", 0, 1)
    P.link(r_edit, 0, g_edit, 1)
    m_e1 = P.msg("1")
    P.link(g_edit, 0, m_e1, 0)
    r_editclr = P.obj("r ---editclr", 0, 1)
    m_e0 = P.msg("0")
    P.link(r_editclr, 0, m_e0, 0)
    sel_dp = P.obj("sel 0 1", 1, 3)
    P.link(m_e1, 0, sel_dp, 0)
    P.link(m_e0, 0, sel_dp, 0)
    on_c = "bgfillcolor " + " ".join(f"{v:.3f}" for v in C_LED_ON)
    off_c = "bgfillcolor " + " ".join(f"{v:.3f}" for v in C_LED_OFF)
    m_dpoff, m_dpon = P.msg(off_c), P.msg(on_c)
    P.link(sel_dp, 0, m_dpoff, 0)
    P.link(sel_dp, 1, m_dpon, 0)
    P.link(m_dpoff, 0, dp_id, 0)
    P.link(m_dpon, 0, dp_id, 0)
    # buttons
    to_cache = P.obj("i", 2, 1)
    P.link(to, 0, to_cache, 1)
    P.link(wr, 0, to_cache, 0)
    P.link(to_cache, 0, s_write, 0)
    # writing into the active program clears its edit flag
    ex_same = P.obj("expr $i1 == $i2", 2, 1)
    P.link(to, 0, ex_same, 1)
    t_w2 = P.obj("t b b", 1, 2)
    P.link(wr, 0, t_w2, 0)
    i_cur2 = P.obj("i", 2, 1)
    P.link(t_p, 0, i_cur2, 1)
    P.link(t_w2, 0, i_cur2, 0)
    P.link(i_cur2, 0, ex_same, 0)
    sel_same = P.obj("sel 1", 2, 2)
    P.link(ex_same, 0, sel_same, 0)
    P.link(sel_same, 0, s_editclr, 0)
    for btn, inc in ((up, "+ 1"), (dn, "+ 9")):
        ii = P.obj("i", 2, 1)
        P.link(t_p, 0, ii, 1)
        P.link(btn, 0, ii, 0)
        a = P.obj(inc, 2, 1)
        P.link(ii, 0, a, 0)
        md = P.obj("% 10", 2, 1)
        P.link(a, 0, md, 0)
        P.link(md, 0, prog, 0)

    # init sequence (live.thisdevice): right-to-left
    #   4: tempo observer  3: close recall gates  2: push every control to gen~ and prime the
    #   program display  1: clear edit flag  0: enable program logic
    m_close = P.msg("0")
    P.link(t_init, 3, m_close, 0)
    P.link(m_close, 0, s_ropen1, 0)
    # v1.0.2-rc3 (D-1): live.thisdevice also bangs on every preset load / device save. Close the
    # program logic before outlet 2 re-outputs Program, so a re-run of this sequence never
    # recalls a program slot over the restored panel; outlet 0 re-opens it.
    P.link(m_close, 0, g_logic, 0)
    for key, (oid, c) in ctrl_ids.items():
        P.link(t_init, 2, oid, 0)
    P.link(t_init, 2, prog, 0)
    P.link(t_init, 2, to, 0)
    P.link(t_init, 1, s_editclr, 0)
    m_open = P.msg("1")
    P.link(t_init, 0, m_open, 0)
    P.link(m_open, 0, g_logic, 0)

    # ------------------------------------------------------ LED display
    def digit_driver(src_out, seg_ids):
        for k in range(7):
            ex = P.obj(f"expr ({SEG_WORD[k]} >> $i1) & 1", 1, 1)
            P.link(src_out, 0, ex, 0)
            ch = P.obj("change", 1, 3, ["", "int", "int"])
            P.link(ex, 0, ch, 0)
            sl = P.obj("sel 0 1", 1, 3)
            P.link(ch, 0, sl, 0)
            mo, mi = P.msg(off_c), P.msg(on_c)
            P.link(sl, 0, mo, 0)
            P.link(sl, 1, mi, 0)
            P.link(mo, 0, seg_ids[k], 0)
            P.link(mi, 0, seg_ids[k], 0)

    # program digit
    digit_driver(t_p, digit_segs[0])
    # delay time digits from gen~ out5
    snap = P.obj("snapshot~ 40", 2, 1, ["float"])
    P.link(gen, 4, snap, 0)
    rnd = P.obj("expr int($f1 + 0.5)", 1, 1)
    P.link(snap, 0, rnd, 0)
    chg = P.obj("change", 1, 3, ["", "int", "int"])
    P.link(rnd, 0, chg, 0)
    exprs = ["($i1 >= 1000) * (($i1 / 1000) % 10) + ($i1 < 1000) * 10",
             "($i1 >= 100) * (($i1 / 100) % 10) + ($i1 < 100) * 10",
             "($i1 >= 10) * (($i1 / 10) % 10) + ($i1 < 10) * 10",
             "$i1 % 10"]
    for i, ex in enumerate(exprs):
        e_ = P.obj("expr " + ex, 1, 1)
        P.link(chg, 0, e_, 0)
        digit_driver(e_, digit_segs[i + 1])

    # headroom meter
    msnap = P.obj("snapshot~ 40", 2, 1, ["float"])
    P.link(gen, 2, msnap, 0)
    for pid, on, off, th in meter_ids:
        ex = P.obj(f"expr $f1 >= {th}", 1, 1)
        P.link(msnap, 0, ex, 0)
        ch = P.obj("change", 1, 3, ["", "int", "int"])
        P.link(ex, 0, ch, 0)
        sl = P.obj("sel 0 1", 1, 3)
        P.link(ch, 0, sl, 0)
        mo = P.msg("bgfillcolor " + " ".join(f"{v:.3f}" for v in off))
        mi = P.msg("bgfillcolor " + " ".join(f"{v:.3f}" for v in on))
        P.link(sl, 0, mo, 0)
        P.link(sl, 1, mi, 0)
        P.link(mo, 0, pid, 0)
        P.link(mi, 0, pid, 0)

    # LFO LED
    lsnap = P.obj("snapshot~ 30", 2, 1, ["float"])
    P.link(gen, 3, lsnap, 0)
    t_ff = P.obj("t f f", 1, 2)
    P.link(lsnap, 0, t_ff, 0)
    er = P.obj("expr 0.20 + 0.80 * $f1", 1, 1)
    eg = P.obj("expr 0.035 + 0.095 * $f1", 1, 1)
    pk = P.obj("pak 0. 0. 0.06 1.", 4, 1)
    P.link(t_ff, 1, eg, 0)
    P.link(t_ff, 0, er, 0)
    P.link(eg, 0, pk, 1)
    P.link(er, 0, pk, 0)
    pb = P.obj("prepend bgfillcolor", 2, 1)
    P.link(pk, 0, pb, 0)
    P.link(pb, 0, lfo_led, 0)

    # ----------------------------------------------------------- patcher
    banks = {
        "0": {"index": 0, "name": "Delay", "parameters": ["Delay Time", "Feedback", "Balance", "Mod Intensity",
                                                          "Mod Frequency", "Low Cut", "High Cut", "Hold"]},
        "1": {"index": 1, "name": "Character", "parameters": ["Input Attenuator", "Input Level", "Preamp Drive",
                                                              "Preamp Tone", "Regen Invert", "Mod Waveform",
                                                              "Output Invert", "Bypass"]},
        "2": {"index": 2, "name": "Modern", "parameters": ["Tempo Sync", "Sync Division", "Time Mode",
                                                           "Time Change", "Stereo Width", "Output Gain",
                                                           "Output Mode", "Wet Only"]},
        # rc5: banks always hold 8 slots; empty slots are "-" (a 2-entry bank made Max look up 6 missing
        # parameters, printing "parameter '<unknown>' not found" each time Live refreshed the bank)
        "3": {"index": 3, "name": "Ext Loop", "parameters": ["FB Route", "Ext Return", "Loop Comp", "Loop Cal"] +
                                                             ["-"] * 4},
        "4": {"index": 4, "name": "Reverse", "parameters": ["Reverse"] + ["-"] * 7},
    }
    params = dict(P.params)
    params["parameterbanks"] = banks
    params["inherited_shortname"] = 1
    patcher = {"patcher": {
        "fileversion": 1, "appversion": APPVERSION, "classnamespace": "box",
        "rect": [60.0, 80.0, 1600.0, 900.0], "openrect": [0.0, 0.0, 0.0, float(DEVICE_H)],
        "bglocked": 0, "openinpresentation": 1, "default_fontsize": 10.0, "default_fontface": 0,
        "default_fontname": "Arial Bold", "gridonopen": 1, "gridsize": [8.0, 8.0], "gridsnaponopen": 1,
        "objectsnaponopen": 1, "statusbarvisible": 2, "toolbarvisible": 1, "lefttoolbarpinned": 0,
        "toptoolbarpinned": 0, "righttoolbarpinned": 0, "bottomtoolbarpinned": 0,
        "toolbars_unpinned_last_save": 0, "tallnewobj": 0, "boxanimatetime": 200, "enablehscroll": 1,
        "enablevscroll": 1, "devicewidth": float(DEVICE_W), "description": "ECHOLIVITY SDD-3000 digital delay",
        "digest": "", "tags": "", "style": "", "subpatcher_template": "", "assistshowspatchername": 0,
        "boxes": P.boxes, "lines": P.lines, "parameters": params, "dependency_cache": [],
        "latency": 0, "is_mpe": 0, "external_mpe_tuning_enabled": 0, "minimum_live_version": "",
        "minimum_max_version": "", "platform_compatibility": 0,
        "project": {"version": 1, "creationdate": 3590052493, "modificationdate": 3590052493,
                    "viewrect": [0.0, 0.0, 300.0, 500.0], "autoorganize": 1, "hideprojectwindow": 1,
                    "showdependencies": 1, "autolocalize": 0, "contents": {"patchers": {}},
                    "layout": {}, "searchpath": {}, "detailsvisible": 0, "amxdtype": 1633771873,
                    "readonly": 0, "devpathtype": 0, "devpath": ".", "sortmode": 0, "viewmode": 0,
                    "includepackages": 0},
        "autosave": 0}}
    # v1.0.2-rc4 (UI-1): in Live 12 the panel showed only the dark backing panel, with no
    # controls drawn. Static backing panels (nothing connects into them) go into Max's background
    # layer, which is always drawn behind the foreground layer (Cycling '74, "Foreground and
    # Background Layers"). Panels that change colour (LEDs, 7-segment digits) stay in the
    # foreground, above their static backing.
    driven = {l["patchline"]["destination"][0] for l in P.lines}
    for b in P.boxes:
        bx = b["box"]
        if bx["maxclass"] == "panel" and bx["id"] not in driven:
            bx["background"] = 1
    return patcher, preview


def validate(patcher):
    p = patcher["patcher"]
    ids = {b["box"]["id"]: b["box"] for b in p["boxes"]}
    assert len(ids) == len(p["boxes"]), "duplicate ids"
    errs = []
    for l in p["lines"]:
        s, so = l["patchline"]["source"]
        d, di = l["patchline"]["destination"]
        if s not in ids or d not in ids:
            errs.append(f"dangling line {s}->{d}")
            continue
        if so >= ids[s]["numoutlets"]:
            errs.append(f"{s} ({ids[s].get('text', ids[s]['maxclass'])}) has no outlet {so}")
        if di >= ids[d]["numinlets"]:
            errs.append(f"{d} ({ids[d].get('text', ids[d]['maxclass'])}) has no inlet {di}")
    for b in p["boxes"]:
        bx = b["box"]
        if bx.get("presentation"):
            x, y, w, h = bx["presentation_rect"]
            if y < 0 or y + h > DEVICE_H + 0.01 or x < 0 or x + w > DEVICE_W + 0.01:
                errs.append(f"{bx['id']} outside the device area: {bx['presentation_rect']}")
    names = [v[0] for k, v in p["parameters"].items() if k.startswith("obj-")]
    assert len(names) == len(set(names)), "duplicate parameter names"
    for bank in p["parameters"]["parameterbanks"].values():
        for n in bank["parameters"]:
            if n not in names and n != "-":
                errs.append("bank refers to unknown parameter " + n)
    if errs:
        raise SystemExit("VALIDATION FAILED:\n  " + "\n  ".join(errs))
    return len(p["boxes"]), len(p["lines"]), len(names)


def write_amxd(patcher, path):
    js = json.dumps(patcher, indent=1, ensure_ascii=False).encode("utf-8") + b"\n\x00"
    data = (b"ampf" + struct.pack("<I", 4) + b"aaaa" +
            b"meta" + struct.pack("<I", 4) + struct.pack("<I", 1) +
            b"ptch" + struct.pack("<I", len(js)) + js)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(data)
    return len(data)


def render_preview(preview, path):
    from PIL import Image, ImageDraw, ImageFont
    S = 2
    im = Image.new("RGB", (DEVICE_W * S, DEVICE_H * S), (0, 0, 0))
    dr = ImageDraw.Draw(im)

    def col(c):
        return tuple(int(255 * v) for v in c[:3])

    def font(sz, bold=True):
        for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
            try:
                return ImageFont.truetype(f, int(sz * S * 0.95))
            except OSError:
                pass
        return ImageFont.load_default()

    for rect, c, rnd in preview["panels"]:
        x, y, w, h = [v * S for v in rect]
        dr.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=min(rnd * S, w / 2, h / 2), fill=col(c))
    for rect, text, c, size, just in preview["labels"]:
        x, y, w, h = [v * S for v in rect]
        f = font(size)
        for i, line in enumerate(text.split("\n")):
            tw = dr.textlength(line, font=f)
            xx = x + (w - tw) / 2 if just == 1 else x
            dr.text((xx, y + 2 + i * size * S * 1.15), line, font=f, fill=col(c))
    for c, legend in preview["controls"]:
        x, y, w, h = [v * S for v in c["rect"]]
        if c["kind"] == "dial":
            r = min(w, h - 22 * S) / 2 * 0.86
            cx, cy = x + w / 2, y + 11 * S + r + 2
            dr.text((x + w / 2 - dr.textlength(c["sn"], font=font(8)) / 2, y), c["sn"], font=font(8), fill=col(legend))
            dr.arc([cx - r, cy - r, cx + r, cy + r], 135, 405, fill=col(C_KNOB), width=int(3 * S))
            frac = (c["init"] - c["lo"]) / (c["hi"] - c["lo"])
            arc = C_ARC_M if c["modern"] else C_ARC
            dr.arc([cx - r, cy - r, cx + r, cy + r], 135, 135 + 270 * frac, fill=col(arc), width=int(3 * S))
            import math
            a = math.radians(135 + 270 * frac)
            dr.line([cx, cy, cx + r * math.cos(a), cy + r * math.sin(a)], fill=col(C_NEEDLE), width=2 * S)
            v = f"{c['init']:.1f}" if c["unit"] in (1,) else (f"{c['init']:.0f} ms" if c["unit"] == 2 else
                                                              f"{c['init']:.1f} dB" if c["unit"] == 4 else f"{c['init']:.0f} %")
            dr.text((x + w / 2 - dr.textlength(v, font=font(7.5, False)) / 2, cy + r + 2), v, font=font(7.5, False), fill=col(legend))
        elif c["kind"] == "tab":
            n = len(c["enum"])
            lines = c.get("lines") or 1
            per = (n + lines - 1) // lines
            cw, chh = w / per, h / lines
            for i, t in enumerate(c["enum"]):
                rr, cc = divmod(i, per)
                xx, yy = x + cc * cw, y + rr * chh
                on = i == c["init"]
                fill = (C_ARC_M if c["modern"] else [0.86, 0.20, 0.12, 1]) if on else C_BTN
                dr.rectangle([xx + 1, yy + 1, xx + cw - 2, yy + chh - 2], fill=col(fill), outline=col([0.3, 0.3, 0.31, 1]))
                f = font(7.0)
                dr.text((xx + cw / 2 - dr.textlength(t, font=f) / 2, yy + chh / 2 - 4 * S), t, font=f,
                        fill=col([0.05, 0.05, 0.05, 1] if on else legend))
        elif c["kind"] in ("text", "menu", "numbox"):
            dr.rectangle([x, y, x + w - 1, y + h - 1], fill=col(C_BTN), outline=col([0.3, 0.3, 0.31, 1]))
            t = c["text"][0] if c["kind"] == "text" else (c["enum"][c["init"]] + " ▾" if c["kind"] == "menu" else
                                                         (f"{c['init']:.1f}" if "lo" in c else "1"))
            f = font(7.5)
            dr.text((x + w / 2 - dr.textlength(t, font=f) / 2, y + h / 2 - 4.5 * S), t, font=f, fill=col(legend))
    im.save(path)


def main():
    patcher, preview = build()
    nb, nl, npar = validate(patcher)
    os.makedirs(os.path.dirname(OUT_PAT), exist_ok=True)
    json.dump(patcher, open(OUT_PAT, "w"), indent=1, ensure_ascii=False)
    size = write_amxd(patcher, OUT_AMXD)
    render_preview(preview, os.path.join(ROOT, "docs", "ui_preview.png"))
    print(f"amxd: {size} bytes, {nb} boxes, {nl} lines, {npar} parameters -> {OUT_AMXD}")


if __name__ == "__main__":
    main()

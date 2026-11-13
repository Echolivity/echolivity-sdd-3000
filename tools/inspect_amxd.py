#!/usr/bin/env python3
"""
inspect_amxd.py -- STATIC integration checks of the distributed .amxd (v1.0.1).

Everything here is inspection of the file; nothing is executed in Max or Live.
Results are written to docs/STATIC_CHECKS.json and are reported as
"PASS (static)" -- never as runtime validation.
"""
import json, os, re, struct, sys, tempfile, shutil, subprocess, hashlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AMXD = os.path.join(ROOT, "dist", "ECHOLIVITY SDD-3000.amxd")
GEN = os.path.join(ROOT, "src", "gen", "echolivity_core.genexpr")
PRE = os.path.join(ROOT, "presets", "factory_programs.json")
OUT = os.path.join(ROOT, "docs", "STATIC_CHECKS.json")
FIELDS = ["time_ms", "feedback", "fb_inv", "lowcut", "highcut", "waveform", "intensity",
          "frequency", "balance", "time_mode", "sync", "division"]
DEVICE_H = 169

R = []


def check(name, ok, detail):
    R.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS (static) " if ok else "FAIL (static) ") + name + " :: " + detail)


def load():
    d = open(AMXD, "rb").read()
    hdr_ok = d[:4] == b"ampf" and struct.unpack("<I", d[4:8])[0] == 4 and d[8:12] == b"aaaa" \
        and d[12:16] == b"meta" and d[24:28] == b"ptch"
    n = struct.unpack("<I", d[28:32])[0]
    body = d[32:32 + n]
    ok = hdr_ok and 32 + n == len(d) and body.endswith(b"\x00")
    pat = json.loads(body.rstrip(b"\x00"))
    check("container", ok and pat["patcher"]["project"]["amxdtype"] == 1633771873,
          f"ampf/aaaa, meta, ptch length {n} = file size - 32, NUL-terminated, JSON parses, amxdtype audio effect")
    return pat["patcher"], d


def main():
    p, raw = load()
    boxes = {b["box"]["id"]: b["box"] for b in p["boxes"]}
    out_edges, in_edges = {}, {}
    for l in p["lines"]:
        s, so = l["patchline"]["source"]
        t, ti = l["patchline"]["destination"]
        out_edges.setdefault((s, so), []).append((t, ti))
        in_edges.setdefault((t, ti), []).append((s, so))

    def succ(oid, outlet=0):
        return [boxes[t] for t, _ in out_edges.get((oid, outlet), [])]

    def text(b):
        return b.get("text", b["maxclass"])

    # --- embedded gen~ code identical to the source
    gen_box = [b for b in boxes.values() if b.get("text") == "gen~"]
    code = [b["box"]["code"] for b in gen_box[0]["patcher"]["boxes"] if b["box"]["maxclass"] == "codebox"][0]
    src = open(GEN).read()
    check("gen~ code == src/gen/echolivity_core.genexpr", code == src,
          f"{len(code)} chars, sha256 {hashlib.sha256(code.encode()).hexdigest()[:16]}...")
    params_gen = {m.group(1): (float(m.group(2)), float(m.group(3)), float(m.group(4)))
                  for m in re.finditer(r"Param\s+(\w+)\(([^,]+),\s*min=([^,]+),\s*max=([^)]+)\);", code)}
    # GenExpr subset compatibility (translator rules) -- static only
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "gen2c.py"), GEN,
                        os.path.join(tempfile.gettempdir(), "echolivity_check.c")], capture_output=True, text=True)
    check("GenExpr subset rules (tools/gen2c.py)", r.returncode == 0,
          (r.stdout or r.stderr).strip() + " -- gen~ compilation itself NOT VERIFIED")

    # --- parameters
    pboxes = {oid: b for oid, b in boxes.items() if b.get("parameter_enable")}
    vo = {oid: b["saved_attribute_attributes"]["valueof"] for oid, b in pboxes.items()}
    names = [v["parameter_longname"] for v in vo.values()]
    stored = [oid for oid, v in vo.items() if v.get("parameter_invisible") == 1]
    visible = [oid for oid in vo if oid not in stored]
    # REVERSE adds one automatable parameter (163 / 43); the 120 program slots are unchanged
    check("parameter count", len(vo) == 163 and len(visible) == 43 and len(stored) == 120,
          f"{len(vo)} parameters: {len(visible)} automatable + {len(stored)} stored-only (program memory)")
    check("parameter names unique", len(set(names)) == len(names), f"{len(set(names))} unique long names")
    pdict = {k: v for k, v in p["parameters"].items() if k.startswith("obj-")}
    check("'parameters' table matches objects", set(pdict) == set(vo) and
          all(pdict[k][0] == vo[k]["parameter_longname"] for k in vo), f"{len(pdict)} entries")
    bad = []
    for oid, v in vo.items():
        lo, hi, ini = v["parameter_mmin"], v["parameter_mmax"], v["parameter_initial"][0]
        if not (lo <= ini <= hi):
            bad.append(v["parameter_longname"])
        if v["parameter_type"] == 2 and len(v["parameter_enum"]) != int(hi) + 1:
            bad.append(v["parameter_longname"] + " (enum size)")
    check("initial values inside ranges / enum sizes", not bad, ", ".join(bad) or "all 158 OK")
    banks = p["parameters"]["parameterbanks"]
    missing = [n for bk in banks.values() for n in bk["parameters"] if n not in names and n != "-"]
    short = [bk["name"] for bk in banks.values() if len(bk["parameters"]) != 8]
    # rc5: every bank must hold exactly 8 slots ("-" = empty). A short bank printed
    # "parameter '<unknown>' not found" repeatedly in Live 12 (found by the owner in rc4).
    check("Push / Configure banks", not missing and not short,
          f"{len(banks)} banks of 8 slots, all names resolve or are '-'" +
          (f"; missing {missing[:4]}" if missing else "") + (f"; not 8 slots: {short}" if short else ""))

    # --- every automatable control reaches the matching gen~ Param with a compatible range
    rows, problems = [], []
    reached = set()
    for oid in visible:
        v = vo[oid]
        chain, scale, cur = [], 1.0, oid
        hops = succ(cur)
        mult = [b for b in hops if text(b).startswith("* ")]
        if mult:
            scale = float(text(mult[0])[2:])
            hops = succ(mult[0]["id"])
        pre = [b for b in hops if text(b).startswith("prepend p_")]
        if not pre:
            continue
        gp = text(pre[0]).split()[1]
        reached.add(gp)
        to_gen = any(text(t) == "gen~" and ti == 0 for t, ti in
                     [(boxes[t], ti) for t, ti in out_edges.get((pre[0]["id"], 0), [])])
        lo, hi = v["parameter_mmin"] * scale, v["parameter_mmax"] * scale
        _, glo, ghi = params_gen.get(gp, (None, None, None))
        if gp not in params_gen or not to_gen:
            problems.append(f"{v['parameter_longname']} -> {gp} not connected")
        elif abs(lo - glo) > 1e-9 or abs(hi - ghi) > 1e-9:
            problems.append(f"{v['parameter_longname']} range {lo}..{hi} != gen {glo}..{ghi}")
        rows.append(gp)
    check("controls -> gen~ Params (name, connection, range)", not problems and len(rows) == 37,   # + REVERSE
          f"{len(rows)} controls verified" + ("; " + "; ".join(problems) if problems else ""))
    unfed = sorted(set(params_gen) - reached)
    check("gen~ Params without a panel control", unfed == ["p_cal", "p_hf_comp", "p_tempo"],
          f"{unfed}: p_cal is sent by the CAL button (rc5), p_tempo is fed by live.observer, "
          "p_hf_comp is an internal engineering switch (default on)")

    # tempo chain
    obs = [b for b in boxes.values() if text(b) == "live.observer"][0]
    feeds = [text(boxes[s]) for s, _ in in_edges.get((obs["id"], 0), [])]
    idsrc = [text(boxes[s]) for s, _ in in_edges.get((obs["id"], 1), [])]
    outs = [text(b) for b in succ(obs["id"])]
    check("tempo sync chain", "property tempo" in feeds and "live.path" in idsrc and "prepend p_tempo" in outs,
          "live.thisdevice -> 'path live_set' -> live.path -> live.observer('property tempo') -> p_tempo -> gen~")

    # audio routing
    pin = [b for b in boxes.values() if text(b) == "plugin~ 1 2 3 4"][0]
    pout = [b for b in boxes.values() if text(b) == "plugout~ 1 2 3 4"][0]
    g = gen_box[0]["id"]
    route_ok = all((g, k) in out_edges.get((pin["id"], k), []) for k in range(4)) \
        and all((pout["id"], k) in out_edges.get((g, k), []) for k in (0, 1)) \
        and (pout["id"], 2) in out_edges.get((g, 5), []) and (pout["id"], 3) in out_edges.get((g, 6), [])
    gp = gen_box[0]["patcher"]
    ins = sorted(b["box"]["text"] for b in gp["boxes"] if b["box"].get("text", "").startswith("in "))
    nout = sum(1 for b in gp["boxes"] if b["box"].get("text", "").startswith("out "))
    uses = all(f"in{k}" in code for k in (3, 4)) and all(f"out{k} =" in code for k in (6, 7))
    check("audio routing incl. EXT loop (rc4)", route_ok and ins == ["in 1", "in 2", "in 3", "in 4"] and nout == 8 and uses,
          "plugin~ 1 2 3 4 -> gen~ in1-4 (3/4 = EXT return); gen~ out1/2 -> plugout~ 1/2, out6/7 -> plugout~ 3/4 "
          "(EXT send) -- Live routing NOT VERIFIED")

    # --- program memory
    progs = json.load(open(PRE))
    by_name = {v["parameter_longname"]: oid for oid, v in vo.items()}
    ctrl_name = {"time_ms": "Delay Time", "feedback": "Feedback", "fb_inv": "Regen Invert", "lowcut": "Low Cut",
                 "highcut": "High Cut", "waveform": "Mod Waveform", "intensity": "Mod Intensity",
                 "frequency": "Mod Frequency", "balance": "Balance", "time_mode": "Time Mode", "sync": "Tempo Sync",
                 "division": "Sync Division"}
    errs = []
    for k in range(10):
        vals = progs["manual"] if k == 0 else progs["programs"][k - 1]["values"]
        for f in FIELDS:
            ln = ("Manual " if k == 0 else f"Mem{k} ") + ctrl_name[f]
            oid = by_name.get(ln)
            if oid is None:
                errs.append("missing " + ln)
                continue
            v = vo[oid]
            cv = vo[by_name[ctrl_name[f]]]
            if v["parameter_initial"][0] != float(vals[f]):
                errs.append(f"{ln} initial {v['parameter_initial'][0]} != preset {vals[f]}")
            if (v["parameter_mmin"], v["parameter_mmax"]) != (cv["parameter_mmin"], cv["parameter_mmax"]):
                errs.append(f"{ln} range differs from control")
            # write path: gate outlet k -> this numbox ; recall path: numbox -> gate 1 -> control
            src = [(boxes[s], so) for s, so in in_edges.get((oid, 0), [])]
            if not any(text(b) == "gate 10" and so == k for b, so in src):
                errs.append(f"{ln}: write gate outlet {k} not connected")
            rec = [b for b in succ(oid) if text(b) == "gate 1"]
            if not rec or not any(t == by_name[ctrl_name[f]] for t, _ in out_edges.get((rec[0]["id"], 0), [])):
                errs.append(f"{ln}: recall path to '{ctrl_name[f]}' missing")
    check("program memory: 10 slots x 12 fields, factory values, write & recall wiring", not errs,
          "; ".join(errs[:6]) or "120 stored-only slots match presets/factory_programs.json; every slot is "
                                  "written by its gate outlet and recalls into its control")

    # send/receive pairing
    sends = {text(b)[2:] for b in boxes.values() if text(b).startswith("s ---")}
    recvs = {text(b)[2:] for b in boxes.values() if text(b).startswith("r ---")}
    check("send/receive pairs", sends == recvs, f"{sorted(sends)}")

    # init sequence
    td = [b for b in boxes.values() if text(b) == "live.thisdevice"][0]
    trig = succ(td["id"])[0]
    pushed = {t for t, _ in out_edges.get((trig["id"], 2), [])}
    missing = [vo[o]["parameter_longname"] for o in visible if o not in pushed and
               vo[o]["parameter_longname"] not in ("Write", "Program Up", "Program Down", "Loop Cal")]
    check("initialisation pushes every stored control value to gen~", not missing,
          f"live.thisdevice -> [{text(trig)}]: outlet 2 bangs {len(pushed)} objects; momentary buttons deliberately "
          "excluded" + (f"; missing: {missing}" if missing else ""))

    # v1.0.2-rc3: LFO "Mod" mapping -- every continuous panel dial declares Modulation Mode 3
    # (Additive); stepped (Enum) and stored-only parameters declare none.
    dials = [o for o in visible if boxes[o]["maxclass"] == "live.dial" or
             (boxes[o]["maxclass"] == "live.numbox" and vo[o]["parameter_type"] == 0
              and vo[o]["parameter_longname"] != "Loop Comp")]   # rc5: a latency value, not modulated
    bad_mod = [vo[o]["parameter_longname"] for o in vo
               if vo[o].get("parameter_modmode", 0) != (3 if o in dials else 0)]
    check("LFO Mod mapping: Modulation Mode Additive on all continuous dials only", len(dials) == 14 and not bad_mod,
          f"{len(dials)} continuous controls (13 dials + RETURN) with parameter_modmode 3; enum/stored-only: none" +
          (f"; wrong: {bad_mod[:6]}" if bad_mod else "") + " -- Live behaviour NOT VERIFIED")

    # v1.0.2-rc3 (D-1): Program is recalled first (order 0), everything else after (order 1);
    # the start-up sequence closes the program logic before it re-outputs Program.
    prog_o = [o for o in vo if vo[o]["parameter_longname"] == "Program"][0]
    bad_ord = [vo[o]["parameter_longname"] for o in vo
               if vo[o].get("parameter_order", 0) != (0 if o == prog_o else 1)]
    t_p = succ(prog_o)[0]
    g_logic = succ(t_p["id"], 1)[0]
    feeders = {(text(boxes[s]), [ (ss, so) for ss, so in in_edges.get((s, 0), [])][0][1] if in_edges.get((s, 0)) else None,
                [ss for ss, so in in_edges.get((s, 0), [])][0] if in_edges.get((s, 0)) else None)
               for s, _ in in_edges.get((g_logic["id"], 0), [])}
    d1_ok = (text(t_p) == "t i i" and text(g_logic) == "gate 1" and ("0", 3, trig["id"]) in feeders
             and ("1", 0, trig["id"]) in feeders)
    check("D-1: program logic closed during the start-up sequence; Program recalled first", d1_ok and not bad_ord,
          f"[{text(trig)}] outlet 3 -> '0' -> [{text(g_logic)}] (before outlet 2 re-outputs Program), outlet 0 -> '1'; "
          f"Program parameter_order 0, other {len(vo) - 1} parameters order 1" +
          (f"; wrong order: {bad_ord[:6]}" if bad_ord else "") + " -- Live behaviour NOT VERIFIED")

    # v1.0.2-rc4 (UI-1): static backing panels in Max's background layer, driven panels in front
    driven = {t for (t, _), _src in in_edges.items()}
    pan = [b for b in boxes.values() if b["maxclass"] == "panel"]
    bad_l = [b["id"] for b in pan if b.get("background", 0) != (0 if b["id"] in driven else 1)]
    nb = sum(1 for b in pan if b.get("background") == 1)
    check("UI-1: backing panels in the background layer, LEDs/segments in front", not bad_l and nb == 20,
          f"{nb} static panels background 1; {len(pan) - nb} driven panels foreground" +
          (f"; wrong: {bad_l[:6]}" if bad_l else "") + " -- confirmed visually in Live 12 by the owner")

    # presentation geometry
    ui = [b for b in boxes.values() if b.get("presentation") and b["maxclass"] not in ("panel", "comment")]
    outside = [text(b) for b in boxes.values() if b.get("presentation") and
               (b["presentation_rect"][1] + b["presentation_rect"][3] > DEVICE_H + 0.01)]
    ov = []
    for i, a in enumerate(ui):
        ax, ay, aw, ah = a["presentation_rect"]
        for b in ui[i + 1:]:
            bx, by, bw, bh = b["presentation_rect"]
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                ov.append(f"{a.get('varname')}/{b.get('varname')}")
    check("presentation layout", not outside and not ov,
          f"{len(ui)} controls inside {DEVICE_H} px, no overlapping controls")

    # deterministic rebuild from source
    tmp = tempfile.mkdtemp()
    try:
        for d in ("tools", "src", "presets", "docs", "dist"):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d))
        subprocess.check_call([sys.executable, os.path.join(tmp, "tools", "make_gen.py")], stdout=subprocess.DEVNULL)
        subprocess.check_call([sys.executable, os.path.join(tmp, "tools", "build_amxd.py")], stdout=subprocess.DEVNULL)
        a = open(os.path.join(tmp, "dist", "ECHOLIVITY SDD-3000.amxd"), "rb").read()
    finally:
        shutil.rmtree(tmp)
    check("distributed .amxd == fresh build from source", a == raw,
          f"sha256 {hashlib.sha256(raw).hexdigest()}")

    json.dump(R, open(OUT, "w"), indent=1)
    n = sum(r["pass"] for r in R)
    print(f"\n{n}/{len(R)} static checks passed")
    sys.exit(0 if n == len(R) else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
check_compat.py -- static preset/parameter compatibility check between two .amxd files.

  python3 tools/check_compat.py OLD.amxd NEW.amxd

Compares every Live parameter definition (long name = Live's identifier for automation, presets and
Sets; short name; type; range; enum; initial value; visibility; unit style; exponent), the Push banks,
and the factory program values stored in the 120 program-memory parameters. Static inspection only:
whether Live actually restores a given Set/.adv is NOT VERIFIED by this tool.
"""
import json, os, struct, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KEYS = ["parameter_shortname", "parameter_type", "parameter_mmin", "parameter_mmax", "parameter_enum",
        "parameter_initial", "parameter_initial_enable", "parameter_invisible", "parameter_unitstyle",
        "parameter_exponent", "parameter_steps"]


def params(path):
    d = open(path, "rb").read()
    n = struct.unpack("<I", d[28:32])[0]
    p = json.loads(d[32:32 + n].rstrip(b"\x00"))["patcher"]
    out = {}
    for b in p["boxes"]:
        bx = b["box"]
        if bx.get("parameter_enable"):
            v = bx["saved_attribute_attributes"]["valueof"]
            out[v["parameter_longname"]] = ({k: v.get(k) for k in KEYS}, bx["maxclass"], bx.get("varname"))
    return out, p["parameters"]["parameterbanks"]


def extra(path):
    """Every parameter attribute NOT in KEYS (e.g. modulation mode, recall order)."""
    d = open(path, "rb").read()
    n = struct.unpack("<I", d[28:32])[0]
    p = json.loads(d[32:32 + n].rstrip(b"\x00"))["patcher"]
    out = {}
    for b in p["boxes"]:
        bx = b["box"]
        if bx.get("parameter_enable"):
            v = bx["saved_attribute_attributes"]["valueof"]
            out[v["parameter_longname"]] = {k: x for k, x in v.items() if k not in KEYS and k != "parameter_longname"}
    return out


def main(old, new):
    a, ba = params(old)
    b, bb = params(new)
    res = {"old": os.path.basename(old), "new": os.path.basename(new), "checks": []}

    def chk(name, ok, detail):
        res["checks"].append({"check": name, "pass": bool(ok), "detail": detail})
        print(("PASS (static) " if ok else "FAIL (static) ") + name + " :: " + detail)

    ADDED = {"FB Route", "Ext Return",          # v1.0.2-rc4: EXT regeneration loop (new parameters only)
             "Loop Comp", "Loop Cal"}           # v1.0.2-rc5: EXT loop latency compensation / calibration
    chk("every old parameter still present; only the rc4/rc5 EXT-loop parameters added",
        set(a) <= set(b) and set(b) - set(a) <= ADDED,
        f"{len(a)} old, {len(b)} new; missing: {sorted(set(a) - set(b))[:5]}; added: {sorted(set(b) - set(a))}")
    diffs = [n for n in a if n in b and a[n] != b[n]]

    # rc5: the 11 Sync Division parameters (panel, manual snapshot, 9 program slots) gained two appended
    # divisions (1/16T, 1/32T) and musician labels. Allowed: the range grows from 0-10 to 0-12 and the
    # enum from 11 to 13 entries; type, initial value, units, visibility, object and name must not change.
    def div_ok(n):
        if not n.endswith("Sync Division"):
            return False
        (oa, ca, va), (ob, cb, vb) = a[n], b[n]
        same = {k: oa[k] == ob[k] for k in oa if k not in ("parameter_mmax", "parameter_enum")}
        ea, eb = oa.get("parameter_enum"), ob.get("parameter_enum")
        enum_ok = (ea is None and eb is None) or (ea is not None and eb is not None and len(eb) == len(ea) + 2)
        return all(same.values()) and ca == cb and va == vb and enum_ok and \
            oa.get("parameter_mmax") in (10, 10.0) and ob.get("parameter_mmax") in (12, 12.0)
    div_changed = [n for n in diffs if div_ok(n)]
    other = [n for n in diffs if n not in div_changed]
    chk("identical definitions (type, range, enum, initial, visibility, units, object, scripting name)",
        not other, f"{len(a) - len(diffs)}/{len(a)} identical; {len(div_changed)} Sync Division parameters "
        f"extended 0-10 -> 0-12 (rc5 triplets appended, old indices unchanged)" +
        (f"; differ: {other[:8]}" if other else ""))
    xa, xb = extra(old), extra(new)
    changed = sorted({k for n in xa if n in xb for k in set(xa[n]) | set(xb[n]) if xa[n].get(k) != xb[n].get(k)})
    nchg = sum(1 for n in xa if n in xb and xa[n] != xb[n])
    chk("other attributes: only Modulation Mode / recall Order differ (intended in 1.0.2-rc3)",
        set(changed) <= {"parameter_modmode", "parameter_order"},
        f"{nchg} parameters differ only in {changed or 'nothing'}")
    chk("Push/Configure banks: the existing banks unchanged",
        all(ba[k] == bb.get(k) for k in ba), f"{len(ba)} old banks identical; {len(bb) - len(ba)} added")
    vis = sum(1 for n in b if not b[n][0]["parameter_invisible"])
    chk("automatable / stored-only split", vis == 38 + len(ADDED & set(b)) and len(b) - vis == 120,
        f"{vis} automatable + {len(b) - vis} stored-only")
    progs = json.load(open(os.path.join(ROOT, "presets", "factory_programs.json")))
    names = {"time_ms": "Delay Time", "feedback": "Feedback", "fb_inv": "Regen Invert", "lowcut": "Low Cut",
             "highcut": "High Cut", "waveform": "Mod Waveform", "intensity": "Mod Intensity",
             "frequency": "Mod Frequency", "balance": "Balance", "time_mode": "Time Mode", "sync": "Tempo Sync",
             "division": "Sync Division"}
    bad = []
    for k in range(10):
        vals = progs["manual"] if k == 0 else progs["programs"][k - 1]["values"]
        for f, ln in names.items():
            pn = ("Manual " if k == 0 else f"Mem{k} ") + ln
            if b[pn][0]["parameter_initial"][0] != float(vals[f]):
                bad.append(pn)
    chk("factory programs in the device == presets/factory_programs.json", not bad,
        "120/120 stored values match" if not bad else f"mismatch: {bad[:6]}")
    out = os.path.join(ROOT, "docs", "validation", "PRESET_COMPATIBILITY.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)
    sys.exit(0 if all(c["pass"] for c in res["checks"]) else 1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

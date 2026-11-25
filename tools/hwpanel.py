"""hwpanel: hardware-replica panels for Echolivity Max for Live devices.

One spec dict describes a device's front panel. render(spec, outdir) writes
faceplate and control filmstrips (1x and @2x PNG). The patch helpers return
Max box fragments: an fpic showing the image, and attribute sets that make the
standard Live control laid over it fully transparent, so automation, MIDI and
modulation mapping, the info view and parameter identities are unchanged.

Spec (all coordinates in 1x pixels, device height normally 169):
  W, H, finish: {"base": (r,g,b), "texture": "brushed"|"painted", "legend": rgb,
                 "dim": rgb, "accent": rgb, "rule": rgb}
  title, subtitle, sections: [(x0, x1, header|None)]
  knobs:   {key: {label, cx, cy, kind: big|mid|small|trim, scale: "numbers"|"ticks"|[legends],
                  positions: n (detented, legends at n angles) }}
  rotary:  {key: {label, cx, cy, box, items:[...], sweep: deg}}       (chicken head)
  toggles: {key: {label, cx, cy, items:[top, (centre,) bottom]}}      (bat handle)
  windows: [(x, y, w, h, caption)]      recessed black windows (menus, readouts)
  vu:      {x, y, caption} or None
  texts:   [(x, y, text, size, style, anchor)]
Rendering is deterministic (fixed RNG seed).
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SS = 4
FONT_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
KNOB_BOX = {"big": 56, "mid": 46, "small": 34, "trim": 30}
TOGGLE_BOX = (22, 36)
VU_BOX = (116, 66)
SWEEP = 135
_L = np.array([-0.45, -0.65, 0.62]); _L /= np.linalg.norm(_L)
_V = np.array([0, 0, 1.0]); _H = (_L + _V) / np.linalg.norm(_L + _V)
CLEAR = [0.0, 0.0, 0.0, 0.0]


# ------------------------------------------------------------------ utilities
def _save(a, outdir, name, scale=2):
    a = np.clip(a, 0, 1)
    h, w = a.shape[:2]
    for s, suffix in ((2, "@2x"), (1, "")):
        f = (scale * SS) // s
        b = a.reshape(h // f, f, w // f, f, 4)
        rgb = (b[..., :3] * b[..., 3:4]).mean(axis=(1, 3)); al = b[..., 3].mean(axis=(1, 3))
        rgb = np.where(al[..., None] > 1e-6, rgb / np.maximum(al[..., None], 1e-6), 0)
        Image.fromarray((np.dstack([rgb, al]) * 255 + 0.5).astype(np.uint8), "RGBA").save(
            os.path.join(outdir, f"{name}{suffix}.png"), optimize=True)


def _shade(n, base, spec, shin, amb=0.18):
    diff = np.clip((n * _L).sum(-1), 0, 1)[..., None]
    sp = np.clip((n * _H).sum(-1), 0, 1)[..., None] ** shin
    return base * (amb + 0.85 * diff) + spec * sp


def _shift(a, dy, dx):
    """shift without wrap-around (fills with 0)"""
    out = np.zeros_like(a)
    h, w = a.shape[:2]
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = a[ys, xs]
    return out


def _blur(a, px):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(px)), dtype=float) / 255


# ------------------------------------------------------------------ controls
def knob_frame(box, value, flutes=30, cap=True, scale=2, sweep=SWEEP, rng=None):
    rng = rng or np.random.default_rng(11)
    N = box * scale * SS
    y, x = np.mgrid[0:N, 0:N].astype(float)
    c = N / 2; R = N * 0.42
    dx, dy = (x - c) / R, (y - c) / R
    r = np.hypot(dx, dy); th = np.arctan2(dx, -dy)
    ang = math.radians(-sweep + 2 * sweep * value)
    img = np.zeros((N, N, 4))
    img[..., 3] = _blur((np.hypot(dx - 0.10, dy - 0.16) < 1.0).astype(float), N * 0.05) * 0.65
    edge = 1 - 0.035 * (0.5 + 0.5 * np.cos(flutes * (th - ang)))
    body = r < edge
    t = np.clip((r - 0.80) / (edge - 0.80 + 1e-9), 0, 1)
    slope = np.where(r > 0.80, t * 2.2, 0)
    gx = slope * dx / (r + 1e-9); gy = slope * dy / (r + 1e-9)
    ridge = np.where(r > 0.80, 0.35 * np.sin(flutes * (th - ang)) * t, 0)
    gx += ridge * (dy / (r + 1e-9)); gy += -ridge * (dx / (r + 1e-9))
    n = np.dstack([-gx, -gy, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    col = _shade(n, np.array([0.055, 0.055, 0.06]), np.array([0.55, 0.55, 0.58]), 28)
    col += (np.clip(1 - np.hypot(dx + 0.25, dy + 0.35) / 0.9, 0, 1) ** 2 * 0.10)[..., None] * (r <= 0.80)[..., None]
    if cap:
        spin = 0.62 + 0.22 * np.cos(2 * (th - math.radians(-35))) + 0.04 * np.sin(r * 260 + rng.normal(0, 0.3, r.shape))
        rim = np.clip((r - 0.47) / 0.05, 0, 1)
        capc = np.dstack([spin * 0.95, spin * 0.96, spin]) * (1 - 0.45 * rim[..., None])
        col = np.where((r < 0.52)[..., None], capc, col)
    px, py = math.sin(ang), -math.cos(ang)
    along = dx * px + dy * py; across = np.abs(dx * py - dy * px)
    lo = 0.56 if cap else 0.18
    ptr = (along > lo) & (along < 0.86) & (across < 0.045)
    col = np.where(ptr[..., None], np.array([0.94, 0.93, 0.88]), col)
    a = body.astype(float)
    img[..., :3] = np.where(body[..., None], col, 0)
    img[..., 3] = np.maximum(a, img[..., 3] * (1 - a))
    return img


def chicken_frame(box, angle_deg, scale=2):
    from scipy import ndimage
    N = box * scale * SS
    y, x = np.mgrid[0:N, 0:N].astype(float)
    c = N / 2; R = N * 0.40
    dx, dy = (x - c) / R, (y - c) / R
    a = math.radians(angle_deg); px, py = math.sin(a), -math.cos(a)
    along = dx * px + dy * py; across = dx * py - dy * px
    base = np.hypot(dx, dy) < 0.55
    halfw = np.where(along > 0, 0.30 * (1 - along / 1.05), 0.30 * (1 + along / 0.75))
    ptr = (along > -0.72) & (along < 1.02) & (np.abs(across) < np.maximum(halfw, 0))
    shape = base | ptr
    d = ndimage.distance_transform_edt(shape) / (R * 0.22)
    hgt = np.clip(d, 0, 1) ** 0.6
    gy, gx = np.gradient(hgt * R * 0.22)
    n = np.dstack([-gx * 1.6, -gy * 1.6, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    col = _shade(n, np.array([0.05, 0.05, 0.055]), np.array([0.6, 0.6, 0.62]), 30)
    line = (along > 0.1) & (along < 0.92) & (np.abs(across) < 0.04)
    col = np.where(line[..., None], np.array([0.94, 0.93, 0.88]), col)
    sh = _blur(_shift(shape.astype(float), int(N * 0.05), int(N * 0.03)), N * 0.04) * 0.6
    img = np.zeros((N, N, 4))
    img[..., :3] = np.where(shape[..., None], col, 0)
    img[..., 3] = np.maximum(shape.astype(float), sh * (1 - shape))
    return img


def toggle_frame(pos, size=TOGGLE_BOX, scale=2):
    """pos: 'up', 'centre' or 'down' (bat handle on a hex nut)."""
    w, h = size
    Wn, Hn = w * scale * SS, h * scale * SS
    y, x = np.mgrid[0:Hn, 0:Wn].astype(float)
    cx, cy = Wn / 2, Hn / 2
    R = Wn * 0.40
    dx, dy = (x - cx) / R, (y - cy) / R
    ang = np.arctan2(dy, dx)
    hexr = np.cos(math.pi / 6) / np.cos(((ang + math.pi / 6) % (math.pi / 3)) - math.pi / 6)
    nut = np.hypot(dx, dy) < hexr
    nutc = 0.55 + 0.25 * np.cos(ang + 2.3) * np.clip(np.hypot(dx, dy), 0, 1)
    bush = np.hypot(dx, dy) < 0.55
    bushc = 0.45 + 0.4 * np.clip(-(dx * 0.6 + dy * 0.8), -1, 1)
    col = np.where(bush[..., None], np.dstack([bushc] * 3), np.dstack([nutc] * 3))
    if pos == "centre":
        ty = cy
        lever = np.zeros_like(nut)
        tip = np.hypot(x - cx, y - ty) < Wn * 0.19
    else:
        sgn = -1 if pos == "up" else 1
        ty = cy + sgn * Hn * 0.40
        t = np.clip((y - cy) / (ty - cy), 0, 1)
        on_lever = ((y - cy) * sgn >= 0) & ((y - cy) * sgn <= abs(ty - cy))
        lever = on_lever & (np.abs(x - cx) < Wn * (0.11 - 0.04 * t))
        tip = np.hypot(x - cx, y - ty) < Wn * 0.16
    lv = lever | tip
    u = np.clip((x - cx) / (Wn * 0.16), -1, 1)
    chrome = 0.35 + 0.55 * np.exp(-((u + 0.35) / 0.25) ** 2) + 0.15 * (1 - np.abs(u))
    tr = Wn * (0.19 if pos == "centre" else 0.16)
    tipc = 0.3 + 0.7 * np.clip(1 - np.hypot(x - cx + Wn * 0.05, y - ty + Wn * 0.05) / tr, 0, 1)
    lcol = np.where(tip, tipc, chrome)
    col = np.where(lv[..., None], np.dstack([lcol, lcol, lcol * 1.03]), col)
    m = lv | nut
    sh = _blur(_shift(m.astype(float), int(Wn * 0.06), int(Wn * 0.04)), Wn * 0.04) * 0.55
    img = np.zeros((Hn, Wn, 4))
    img[..., :3] = np.where(m[..., None], col, 0)
    img[..., 3] = np.maximum(m.astype(float), sh * (1 - m))
    return img


def vu_pos(db):
    return (10 ** (db / 20) - 0.1) / 1.3125


def vu_frame(pos, size=VU_BOX, scale=2):
    w, h = size
    Wn, Hn = w * scale * SS, h * scale * SS
    y, x = np.mgrid[0:Hn, 0:Wn].astype(float)
    vign = 1 - 0.35 * (((x - Wn / 2) / (Wn / 2)) ** 2 + ((y - Hn * 0.7) / Hn) ** 2)
    face = Image.fromarray((np.clip(np.dstack([0.98 * vign, 0.86 * vign, 0.58 * vign, np.ones_like(vign)]), 0, 1) * 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(face)
    px0, py0, Rr = Wn / 2, Hn * 1.18, Hn * 0.90
    def at(p, rr):
        a = math.radians(-44 + 88 * p)
        return px0 + rr * math.sin(a), py0 - rr * math.cos(a)
    for p0 in np.linspace(0, vu_pos(0), 120):
        d.line([*at(p0, Rr), *at(p0 + 0.006, Rr)], fill=(20, 18, 14, 255), width=int(SS * scale * 0.9))
    for p0 in np.linspace(vu_pos(0), 1, 60):
        d.line([*at(p0, Rr), *at(p0 + 0.006, Rr)], fill=(190, 30, 20, 255), width=int(SS * scale * 2.4))
    fnt = ImageFont.truetype(FONT_B, int(6.5 * scale * SS))
    for db, lab in [(-20, "20"), (-10, "10"), (-7, "7"), (-5, "5"), (-3, "3"), (-2, "2"), (-1, "1"), (0, "0"), (1, "1"), (2, "2"), (3, "3")]:
        p = vu_pos(db)
        colr = (190, 30, 20, 255) if db > 0 else (20, 18, 14, 255)
        d.line([*at(p, Rr), *at(p, Rr + Hn * 0.07)], fill=colr, width=int(SS * scale * 0.8))
        if db in (-20, -10, -7, -5, -3, -1, 0, 1, 3):
            d.text(at(p, Rr + Hn * 0.15), lab, font=fnt, fill=colr, anchor="mm")
    d.text((Wn * 0.11, Hn * 0.16), "–", font=fnt, fill=(20, 18, 14, 255), anchor="mm")
    d.text((Wn * 0.89, Hn * 0.16), "+", font=fnt, fill=(190, 30, 20, 255), anchor="mm")
    d.text((Wn / 2, Hn * 0.66), "VU", font=ImageFont.truetype(FONT_B, int(11 * scale * SS)), fill=(20, 18, 14, 255), anchor="mm")
    xa, ya = at(pos, Rr + Hn * 0.06); xb, yb = at(pos, Hn * 0.30)
    d.line([xb + SS * 3, yb + SS * 4, xa + SS * 3, ya + SS * 4], fill=(60, 45, 20, 90), width=int(SS * scale * 1.2))
    d.line([xb, yb, xa, ya], fill=(15, 15, 15, 255), width=int(SS * scale * 0.9))
    d.rectangle([0, Hn * 0.80, Wn, Hn], fill=(22, 22, 24, 255))
    a = np.asarray(face, dtype=float) / 255
    sheen = np.clip(1 - np.abs((x / Wn) + (y / Hn) * 0.6 - 0.55) / 0.22, 0, 1) * 0.10
    a[..., :3] = np.clip(a[..., :3] + sheen[..., None], 0, 1)
    a[..., :3] *= (0.6 + 0.4 * np.clip(y / (Hn * 0.12), 0, 1))[..., None]
    return a


# ------------------------------------------------------------------ geometry
def knob_box(spec, kind):
    return {**KNOB_BOX, **spec.get("knob_boxes", {})}[kind]


def knob_angle(spec_knob, p):
    """p in 0..1 -> degrees clockwise from up"""
    sw = spec_knob.get("sweep", SWEEP)
    return -sw + 2 * sw * p


def rotary_angles(r):
    n = len(r["items"]); sw = r.get("sweep", 60)
    return [(-sw + 2 * sw * i / (n - 1)) if n > 1 else 0 for i in range(n)]


def toggle_positions(n):
    return ["up", "down"] if n == 2 else ["up", "centre", "down"]


# ------------------------------------------------------------------ faceplate
def faceplate(spec, outdir, scale=2):
    W, H = spec["W"], spec.get("H", 169)
    fin = spec["finish"]
    k = scale * SS
    Wn, Hn = W * k, H * k
    rng = np.random.default_rng(7)
    base = np.array(fin["base"], float) / 255
    if fin.get("texture", "brushed") == "brushed":
        noise = rng.normal(0, 1, (Hn, max(Wn // 16, 1)))
        tex = np.asarray(Image.fromarray(((noise * 20 + 128).clip(0, 255)).astype(np.uint8)).resize((Wn, Hn), Image.BILINEAR), float) / 255 - 0.5
        tex *= 0.08
    else:  # painted / stippled
        noise = rng.normal(0, 1, (Hn // 3, Wn // 3))
        tex = np.asarray(Image.fromarray(((noise * 30 + 128).clip(0, 255)).astype(np.uint8)).resize((Wn, Hn), Image.BILINEAR), float) / 255 - 0.5
        tex *= 0.05
    yy = np.mgrid[0:Hn, 0:Wn][0].astype(float)
    shade = 1 + 0.18 * (1 - yy / Hn) - 0.09
    img = np.dstack([np.clip(base[i] * shade + tex * (0.3 + base[i]), 0, 1) for i in range(3)] + [np.ones_like(yy)])
    e = int(1.5 * k)
    img[:e, :, :3] += 0.10; img[-e:, :, :3] -= 0.04
    img[:, :e, :3] += 0.05; img[:, -e:, :3] -= 0.03
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(im)
    LEG = tuple(fin["legend"]) + (255,)
    DIM = tuple(fin.get("dim", fin["legend"])) + (255,)
    ACC = tuple(fin.get("accent", fin["legend"])) + (255,)
    RULE = tuple(fin.get("rule", (90, 90, 88))) + (255,)
    def F(sz, bold=True): return ImageFont.truetype(FONT_B if bold else FONT_R, int(sz * k))
    def P(xx, yy): return (xx * k, yy * k)
    for x0, x1, hdr in spec.get("sections", []):
        if x0 > 0:
            d.line([P(x0, 10), P(x0, H - 10)], fill=RULE, width=max(1, int(0.6 * k)))
        if hdr:
            d.text(P(x0 + 9, 8), hdr, font=F(6.5), fill=DIM)
    if spec.get("title"):
        tx, ty = spec.get("title_pos", (18, 12))
        d.text(P(tx, ty), spec["title"], font=F(spec.get("title_size", 17)), fill=ACC)
    if spec.get("subtitle"):
        tx, ty = spec.get("subtitle_pos", (19, 32))
        d.text(P(tx, ty), spec["subtitle"], font=F(6.2), fill=DIM)
    for kname, kn in spec.get("knobs", {}).items():
        box = knob_box(spec, kn["kind"])
        cx, cy = kn["cx"], kn["cy"]
        rk = box * 0.42
        big = kn["kind"] in ("big", "mid")
        r1, r2 = rk + (3.5 if big else 2.5), rk + (7 if big else 5)
        scale_kind = kn.get("scale", "numbers" if big else "ticks")
        if scale_kind == "none":
            pass
        elif isinstance(scale_kind, list):          # detented legends
            n = len(scale_kind)
            for i, lab in enumerate(scale_kind):
                a = math.radians(knob_angle(kn, i / (n - 1)))
                d.line([P(cx + r1 * math.sin(a), cy - r1 * math.cos(a)), P(cx + r2 * math.sin(a), cy - r2 * math.cos(a))], fill=LEG, width=max(1, int(0.9 * k)))
                rr = r2 + kn.get("legend_r", 9)
                d.text(P(cx + rr * math.sin(a), cy - rr * math.cos(a)), lab, font=F(kn.get("legend_size", 5.8)), fill=LEG, anchor="mm")
        else:
            n = 11 if kn["kind"] != "trim" else 9
            for i in range(n):
                a = math.radians(knob_angle(kn, i / (n - 1)))
                major = (i % 5 == 0) if kn["kind"] != "trim" else (i % 4 == 0)
                rr = r2 if major else (r1 + r2) / 2 + 0.5
                d.line([P(cx + r1 * math.sin(a), cy - r1 * math.cos(a)), P(cx + rr * math.sin(a), cy - rr * math.cos(a))], fill=LEG, width=max(1, int((0.9 if major else 0.6) * k)))
                if scale_kind == "numbers" and i in (0, 5, 10):
                    lab = kn.get("numbers", ["0", "5", "10"])[(0, 5, 10).index(i)]
                    d.text(P(cx + (r2 + 6) * math.sin(a), cy - (r2 + 6) * math.cos(a)), lab, font=F(5.6, False), fill=DIM, anchor="mm")
        if kn.get("centre_mark"):
            d.polygon([P(cx - 2, cy - r2 - 4), P(cx + 2, cy - r2 - 4), P(cx, cy - r2 - 1)], fill=LEG)
        if kn.get("label"):
            ly = cy - r2 - kn.get("label_gap", 15 if big else 11)
            d.text(P(cx, ly), kn["label"], font=F(7.2 if big else 6.2), fill=LEG, anchor="mm")
    for rname, r in spec.get("rotary", {}).items():
        cx, cy, box = r["cx"], r["cy"], r["box"]
        rr0 = box * 0.40
        for item, a in zip(r["items"], rotary_angles(r)):
            ar = math.radians(a)
            d.line([P(cx + (rr0 + 2) * math.sin(ar), cy - (rr0 + 2) * math.cos(ar)), P(cx + (rr0 + 6) * math.sin(ar), cy - (rr0 + 6) * math.cos(ar))], fill=LEG, width=int(0.9 * k))
            lr = rr0 + r.get("legend_r", 13)
            d.text(P(cx + lr * math.sin(ar), cy - lr * math.cos(ar)), item, font=F(r.get("legend_size", 6.0)), fill=LEG, anchor="mm")
        if r.get("label"):
            d.text(P(cx, cy + r.get("label_dy", box * 0.5 + 6)), r["label"], font=F(7.2), fill=LEG, anchor="mm")
    for tname, t in spec.get("toggles", {}).items():
        cx, cy = t["cx"], t["cy"]
        items = t["items"]
        ys = [-11, 11] if len(items) == 2 else [-12, 0, 12]
        for item, dy in zip(items, ys):
            d.text(P(cx + 14, cy + dy), item, font=F(6.0), fill=LEG, anchor="lm")
        if t.get("label"):
            if t.get("label_above"):
                d.text(P(cx, cy - 24), t["label"], font=F(6.4), fill=LEG, anchor="mm")
            else:
                d.text(P(cx - 14, cy), t["label"], font=F(6.4), fill=LEG, anchor="rm")
    for (x0, y0, w0, h0, cap) in spec.get("windows", []):
        d.rectangle([P(x0 - 1, y0 - 1), P(x0 + w0 + 1, y0 + h0 + 1)], fill=(4, 4, 5, 255), outline=(70, 70, 70, 255), width=int(0.6 * k))
        if cap:
            d.text(P(x0, y0 - 6), cap, font=F(6.0), fill=DIM, anchor="lm")
    if spec.get("vu"):
        vx, vy = spec["vu"]["x"], spec["vu"]["y"]; vw, vh = VU_BOX
        d.rounded_rectangle([P(vx - 4, vy - 4), P(vx + vw + 4, vy + vh + 4)], radius=4 * k, fill=(10, 10, 11, 255), outline=(120, 120, 118, 255), width=int(0.8 * k))
        if spec["vu"].get("caption"):
            d.text(P(vx + vw / 2, vy + vh + 13), spec["vu"]["caption"], font=F(5.6), fill=DIM, anchor="mm")
    for (tx, ty, text, size, style, anchor) in spec.get("texts", []):
        colr = {"legend": LEG, "dim": DIM, "accent": ACC}[style]
        d.text(P(tx, ty), text, font=F(size), fill=colr, anchor=anchor)
    ears = spec.get("ears")
    if ears:
        for x0 in (0, W - ears):
            d.rectangle([P(x0, 0), P(x0 + ears, H)], fill=tuple(int(v * 0.72) for v in fin["base"]) + (255,))
            d.line([P(x0 + (ears if x0 == 0 else 0), 0), P(x0 + (ears if x0 == 0 else 0), H)], fill=(0, 0, 0, 255), width=int(0.8 * k))
            for yc in (20, H - 22):
                cx = x0 + ears / 2
                d.rounded_rectangle([P(cx - 3.2, yc - 5), P(cx + 3.2, yc + 5)], radius=3 * k, fill=(4, 4, 4, 255))
                d.rounded_rectangle([P(cx - 3.2, yc - 5), P(cx + 3.2, yc - 3.5)], radius=1 * k, fill=(0, 0, 0, 255))
    screws = [] if ears else [(9, 9), (W - 9, 9), (9, H - 9), (W - 9, H - 9)]
    for sx, sy in screws:
        rr = 4.2
        d.ellipse([P(sx - rr, sy - rr), P(sx + rr, sy + rr)], fill=(150, 150, 152, 255), outline=(40, 40, 40, 255), width=int(0.5 * k))
        d.ellipse([P(sx - rr + 1.2, sy - rr + 1.2), P(sx + rr - 2, sy + rr - 2)], fill=(200, 200, 202, 255))
        d.line([P(sx - 2.6, sy), P(sx + 2.6, sy)], fill=(35, 35, 35, 255), width=int(0.9 * k))
        d.line([P(sx, sy - 2.6), P(sx, sy + 2.6)], fill=(35, 35, 35, 255), width=int(0.9 * k))
    _save(np.asarray(im, float) / 255, outdir, spec.get("prefix", "") + "faceplate", scale)


# ------------------------------------------------------------------ render all
def render(spec, outdir):
    os.makedirs(outdir, exist_ok=True)
    pre = spec.get("prefix", "")
    faceplate(spec, outdir)
    kinds = sorted({kn["kind"] for kn in spec.get("knobs", {}).values()})
    for kind in kinds:
        box = knob_box(spec, kind)
        fl = {"big": 30, "mid": 26, "small": 22, "trim": 18}.get(kind, max(18, min(30, box // 2)))
        strip = np.concatenate([knob_frame(box, v, flutes=fl, cap=(kind != "trim")) for v in np.linspace(0, 1, 101)], 0)
        _save(strip, outdir, f"{pre}knob_{kind}")
    for rname, r in spec.get("rotary", {}).items():
        _save(np.concatenate([chicken_frame(r["box"], a) for a in rotary_angles(r)], 0), outdir, f"{pre}rotary_{rname}")
    ns = sorted({len(t["items"]) for t in spec.get("toggles", {}).values()})
    for n in ns:
        _save(np.concatenate([toggle_frame(p) for p in toggle_positions(n)], 0), outdir, f"{pre}toggle{n}")
    if spec.get("vu"):
        _save(np.concatenate([vu_frame(p) for p in np.linspace(0, 1, 64)], 0), outdir, f"{pre}vu")
    return sorted(f for f in os.listdir(outdir) if f.endswith(".png"))


# ------------------------------------------------------------------ patch helpers
def image_name(spec, kind, key=None):
    pre = spec.get("prefix", "")
    if kind == "knob":
        return f"{pre}knob_{spec['knobs'][key]['kind']}.png"
    if kind == "rotary":
        return f"{pre}rotary_{key}.png"
    if kind == "toggle":
        return f"{pre}toggle{len(spec['toggles'][key]['items'])}.png"
    if kind == "vu":
        return f"{pre}vu.png"
    return f"{pre}faceplate.png"


def rect(spec, kind, key=None):
    if kind == "knob":
        kn = spec["knobs"][key]; b = knob_box(spec, kn["kind"])
        return [round(kn["cx"] - b / 2, 1), round(kn["cy"] - b / 2, 1), b, b]
    if kind == "rotary":
        r = spec["rotary"][key]; b = r["box"]
        return [r["cx"] - b // 2, r["cy"] - b // 2, b, b]
    if kind == "toggle":
        t = spec["toggles"][key]; w, h = TOGGLE_BOX
        return [t["cx"] - w // 2, t["cy"] - h // 2, w, h]
    if kind == "vu":
        return [spec["vu"]["x"], spec["vu"]["y"], VU_BOX[0], VU_BOX[1]]
    return [0, 0, spec["W"], spec.get("H", 169)]


def fpic_box(box_id, pic, prect, patching_xy, background=False):
    b = {"id": box_id, "maxclass": "fpic", "pic": pic, "autofit": 0, "numinlets": 1, "numoutlets": 0,
         "presentation": 1, "presentation_rect": list(prect),
         "patching_rect": [patching_xy[0], patching_xy[1], prect[2], prect[3]]}
    if background:
        b["background"] = 1
    return b


CLEAR_DIAL = {"showname": 0, "shownumber": 0, "triangle": 0, "activedialcolor": CLEAR, "dialcolor": CLEAR,
              "activeneedlecolor": CLEAR, "needlecolor": CLEAR, "textcolor": CLEAR,
              "focusbordercolor": CLEAR, "tricolor": CLEAR}
CLEAR_TAB = {"bgcolor": CLEAR, "bgoncolor": CLEAR, "activebgcolor": CLEAR, "activebgoncolor": CLEAR,
             "textcolor": CLEAR, "textoncolor": CLEAR, "activetextcolor": CLEAR, "activetextoncolor": CLEAR,
             "bordercolor": CLEAR, "focusbordercolor": CLEAR}
CLEAR_TEXT = {"bgcolor": CLEAR, "bgoncolor": CLEAR, "activebgcolor": CLEAR, "activebgoncolor": CLEAR,
              "textcolor": CLEAR, "textoncolor": CLEAR, "bordercolor": CLEAR, "focusbordercolor": CLEAR,
              "text": "", "texton": ""}


def knob_frame_expr(box, lo=0.0, hi=100.0, exponent=1.0, steps=None):
    """expr text: control value -> fpic y offset (negative) in a 101-frame strip.
    steps=n: detented control, value is an index 0..n-1 (rounded), shown at its legend angle."""
    if steps:
        return f"-int(int(max(0, min({steps - 1}, $f1 + 0.5))) * 100. / {steps - 1} + 0.5) * {box}"
    span = hi - lo
    pos = f"max(0., min(1., ($f1 - {lo}) / {span}))"
    if abs(exponent - 1.0) > 1e-9:
        pos = f"pow({pos}, {1.0 / exponent!r})"
    return f"-int({pos} * 100. + 0.5) * {box}"


def index_frame_expr(height):
    return f"-int($f1 + 0.5) * {height}"


# ------------------------------------------------------------------ preview
def compose_preview(spec, media_dir, values, out_png, extra=None):
    """Composite faceplate + every control at the frame for `values`
    (knobs: 0..1 position; rotary/toggle: index). For visual review only."""
    s = 2
    pre = spec.get("prefix", "")
    bg = Image.open(os.path.join(media_dir, f"{pre}faceplate@2x.png")).convert("RGBA")
    def frame(name, h, idx):
        im = Image.open(os.path.join(media_dir, name.replace(".png", "@2x.png")))
        return im.crop((0, idx * h * s, im.width, (idx + 1) * h * s))
    for key, kn in spec.get("knobs", {}).items():
        r = rect(spec, "knob", key)
        bg.alpha_composite(frame(image_name(spec, "knob", key), r[3], int(round(100 * values.get(key, 0.5)))), (r[0] * s, r[1] * s))
    for key in spec.get("rotary", {}):
        r = rect(spec, "rotary", key)
        bg.alpha_composite(frame(image_name(spec, "rotary", key), r[3], int(values.get(key, 0))), (r[0] * s, r[1] * s))
    for key in spec.get("toggles", {}):
        r = rect(spec, "toggle", key)
        bg.alpha_composite(frame(image_name(spec, "toggle", key), r[3], int(values.get(key, 0))), (r[0] * s, r[1] * s))
    if spec.get("vu"):
        r = rect(spec, "vu")
        bg.alpha_composite(frame(image_name(spec, "vu"), r[3], int(values.get("vu", 30))), (r[0] * s, r[1] * s))
    if extra:
        extra(bg, s)
    bg.save(out_png)


def simulate_patch(maxpat, media_dir, out_png, values=None, scale=2):
    """Approximate presentation view of a device from its .maxpat, for review: background
    layer first, then foreground, each in box order. fpics are drawn at the frame their
    control selects (the patch's own expr evaluated at the control's initial value or
    values[id]); panels, comments, live.tab/text/menu/numbox and live.dial text are drawn
    simply. Asserts each driven fpic whose control is in presentation is aligned with it
    unless allow_offset (knob images smaller than their live.dial)."""
    import json
    p = json.load(open(maxpat))["patcher"]
    B = {b["box"]["id"]: b["box"] for b in p["boxes"]}
    src = {}
    for l in p["lines"]:
        src.setdefault(l["patchline"]["destination"][0], []).append(l["patchline"]["source"][0])
    W = int(p.get("devicewidth") or 400)
    out = Image.new("RGBA", (W * scale, 169 * scale), (0, 0, 0, 255))
    d = ImageDraw.Draw(out)
    values = values or {}
    def C(c, a=None):
        c = c or [1, 1, 1, 1]
        return tuple(int(v * 255) for v in c[:3]) + (int(255 * (c[3] if len(c) > 3 else 1)) if a is None else a,)
    def init(b):
        return values.get(b["id"], b.get("saved_attribute_attributes", {}).get("valueof", {}).get("parameter_initial", [0])[0])
    def R(r): return [r[0] * scale, r[1] * scale, (r[0] + r[2]) * scale, (r[1] + r[3]) * scale]
    fnt = lambda sz: ImageFont.truetype(FONT_B, max(6, int(sz * scale * 0.95)))
    order = [b["box"] for b in p["boxes"] if b["box"].get("presentation")]
    order = [b for b in order if b.get("background")] + [b for b in order if not b.get("background")]
    for b in order:
        x, y, w, h = b["presentation_rect"]
        mc = b["maxclass"]
        if mc == "fpic":
            im = Image.open(os.path.join(media_dir, b["pic"].replace(".png", "@2x.png"))).convert("RGBA")
            off = 0
            if b["id"] in src:
                pre = src[b["id"]][0]; ex = src[pre][0]; ctrl = src[ex][0]
                c = B[ctrl]
                e = B[ex]["text"][5:].replace("$f1", repr(float(init(c)))).replace("$i1", str(int(init(c))))
                off = int(eval(e, {"int": int, "max": max, "min": min, "pow": pow}))
            out.alpha_composite(im.crop((0, int(-off * scale), int(w * scale), int((-off + h) * scale))), (int(x * scale), int(y * scale)))
        elif mc == "panel":
            col = b.get("bgcolor", [0, 0, 0, 1])
            # LEDs etc. are driven at run time; draw their stored colour
            d.rounded_rectangle(R(b["presentation_rect"]), radius=b.get("rounded", 0) * scale * 0.5, fill=C(col))
        elif mc in ("comment", "live.comment"):
            col = C(b.get("textcolor", [1, 1, 1, 1]))
            if b.get("textjustification") == 1:
                d.text(((x + w / 2) * scale, (y + h / 2) * scale), b["text"], font=fnt(b.get("fontsize", 9)), fill=col, anchor="mm")
            else:
                d.text((x * scale, y * scale), b["text"], font=fnt(b.get("fontsize", 9)), fill=col)
        elif mc == "live.tab":
            va = b["saved_attribute_attributes"]["valueof"]; items = va["parameter_enum"]
            n = len(items); lines = b.get("num_lines_presentation", 1); per = math.ceil(n / lines)
            for i, t in enumerate(items):
                r_, c_ = divmod(i, per)
                cw, ch = w / per, h / lines
                rr = [x + c_ * cw, y + r_ * ch, cw - 1, ch - 1]
                on = i == int(init(b))
                bg = b.get("bgoncolor" if on else "bgcolor", [0.2, 0.2, 0.2, 1])
                if bg[3:] and bg[3] == 0:
                    continue
                d.rectangle(R(rr), fill=C(bg))
                d.text(((rr[0] + rr[2] / 2) * scale, (rr[1] + rr[3] / 2) * scale), t, font=fnt(b.get("fontsize", 8) * 0.9),
                       fill=C(b.get("textoncolor" if on else "textcolor", [1, 1, 1, 1])), anchor="mm")
        elif mc == "live.text":
            on = int(init(b)) == 1
            bg = b.get("bgoncolor" if on else "bgcolor", [0.2, 0.2, 0.2, 1])
            if not (bg[3:] and bg[3] == 0):
                d.rounded_rectangle(R(b["presentation_rect"]), radius=2 * scale, fill=C(bg))
                d.text(((x + w / 2) * scale, (y + h / 2) * scale), b.get("texton" if on else "text", ""), font=fnt(7.5),
                       fill=C(b.get("textoncolor" if on else "textcolor", [1, 1, 1, 1])), anchor="mm")
        elif mc in ("live.menu", "umenu"):
            va = b.get("saved_attribute_attributes", {}).get("valueof", {})
            items = va.get("parameter_enum", ["-"])
            d.rectangle(R(b["presentation_rect"]), fill=C(b.get("bgcolor", [0.1, 0.1, 0.1, 1])))
            d.text(((x + 4) * scale, (y + h / 2) * scale), str(items[int(init(b)) if items else 0]) + " ▾", font=fnt(7.5),
                   fill=C(b.get("textcolor", [0.9, 0.9, 0.9, 1])), anchor="lm")
        elif mc == "live.numbox":
            d.rectangle(R(b["presentation_rect"]), outline=C(b.get("bordercolor", [0.3, 0.3, 0.3, 1])), width=scale)
            d.text(((x + w / 2) * scale, (y + h / 2) * scale), f"{init(b):g}", font=fnt(8), fill=C(b.get("textcolor", [1, 1, 1, 1])), anchor="mm")
        elif mc == "live.dial":
            va = b["saved_attribute_attributes"]["valueof"]
            col = C(b.get("textcolor", [1, 1, 1, 1]))
            if col[3] and b.get("showname", 1):
                d.text(((x + w / 2) * scale, (y + 6) * scale), va.get("parameter_shortname", ""), font=fnt(b.get("fontsize", 9)), fill=col, anchor="mm")
            if col[3] and b.get("shownumber", 1):
                d.text(((x + w / 2) * scale, (y + h - 5) * scale), f"{init(b):g}", font=fnt(8), fill=col, anchor="mm")
    out.save(out_png)

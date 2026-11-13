// ECHOLIVITY SDD-3000 - FB ROUTE chooser (embedded in the device as a v8.codebox; requires Live 12.2+ / Max 9)
// Picks where the regeneration SEND (device outputs 3/4) goes and where the RETURN (device inputs 3/4)
// comes from, through the Live Object Model: MaxDevice.audio_outputs[1] / audio_inputs[1] are DeviceIO
// objects whose routing_type (track) and routing_channel (tap) can be set to any of their
// available_routing_types / available_routing_channels. The routing itself is Live's state; this script
// only lists what Live offers and applies the user's choice, and follows changes made anywhere else.
autowatch = 0;
inlets = 1;
outlets = 4;    // 0 SEND track menu, 1 SEND channel menu, 2 RETURN track menu, 3 RETURN channel menu

const IO = {
    send: { path: "this_device audio_outputs 1", menus: [0, 1] },
    ret: { path: "this_device audio_inputs 1", menus: [2, 3] },
};
const PROPS = ["routing_type", "routing_channel", "available_routing_types", "available_routing_channels"];
let state = { send: null, ret: null };
let watchers = [];
let refreshTask = null;
let started = false;

function parseDict(v, key) {
    // dictionary properties arrive as JSON text (sometimes as an atom list)
    const tries = Array.isArray(v) ? [v.join(" "), v.join(","), String(v[v.length - 1])] : [String(v)];
    for (const s of tries) {
        try {
            const o = JSON.parse(s);
            return key in o ? o[key] : o;
        } catch (e) { /* next form */ }
    }
    return null;
}

function api(path) {
    const a = new LiveAPI(path);
    return (a && a.id && Number(a.id) !== 0) ? a : null;
}

function read(which) {
    const a = api(IO[which].path);
    if (!a) return null;
    return {
        types: parseDict(a.get("available_routing_types"), "available_routing_types") || [],
        chans: parseDict(a.get("available_routing_channels"), "available_routing_channels") || [],
        type: parseDict(a.get("routing_type"), "routing_type") || {},
        chan: parseDict(a.get("routing_channel"), "routing_channel") || {},
    };
}

function fill(menu, list, cur) {
    outlet(menu, "clear");
    let sel = -1;
    list.forEach((it, i) => {
        outlet(menu, "append", String(it.display_name));
        if (cur && String(it.identifier) === String(cur.identifier)) sel = i;
    });
    if (!list.length) outlet(menu, "append", "-");
    outlet(menu, "set", Math.max(sel, 0));
}

function refresh() {
    for (const which of ["send", "ret"]) {
        const s = read(which);
        state[which] = s;
        const [mt, mc] = IO[which].menus;
        if (!s) {
            outlet(mt, "clear"); outlet(mt, "append", "(needs Live 12.2+)"); outlet(mt, "set", 0);
            outlet(mc, "clear"); outlet(mc, "append", "-"); outlet(mc, "set", 0);
            continue;
        }
        fill(mt, s.types, s.type);
        fill(mc, s.chans, s.chan);
    }
}

function scheduleRefresh() {
    // never touch Live from inside a notification; defer
    if (!refreshTask) refreshTask = new Task(refresh);
    refreshTask.cancel();
    refreshTask.schedule(20);
}

function applyChoice(which, prop, item) {
    const a = api(IO[which].path);
    if (!a || !item) return;
    const want = String(item.identifier);
    const forms = [{ identifier: item.identifier }, JSON.stringify({ identifier: item.identifier })];
    for (const f of forms) {
        try { a.set(prop, f); } catch (e) { continue; }
        const now = parseDict(a.get(prop), prop);
        if (now && String(now.identifier) === want) break;
    }
    scheduleRefresh();
}

function choose(which, kind, i) {
    const s = state[which] || read(which);
    if (!s) return;
    const list = kind === "type" ? s.types : s.chans;
    applyChoice(which, kind === "type" ? "routing_type" : "routing_channel", list[i]);
}

function init() {
    if (!started) {
        for (const which of ["send", "ret"]) {
            for (const p of PROPS) {
                const w = new LiveAPI(scheduleRefresh, IO[which].path);
                if (w && w.id && Number(w.id) !== 0) {
                    w.property = p;
                    watchers.push(w);
                }
            }
        }
        started = true;
    }
    refresh();
}

function bang() { init(); }
function sendtype(i) { choose("send", "type", i); }
function sendchan(i) { choose("send", "chan", i); }
function rettype(i) { choose("ret", "type", i); }
function retchan(i) { choose("ret", "chan", i); }

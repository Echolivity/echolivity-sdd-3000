// Offline logic test for src/max/fb_route_chooser.js with a mock Live Object Model (node).
// It cannot prove Live behaviour; it checks the script's own logic: menu filling, selection mapping,
// applying a choice, following external changes, and the no-Live fallback.
const fs = require("fs");
const code = fs.readFileSync(__dirname + "/../../src/max/fb_route_chooser.js", "utf8");
let fails = 0;
const ok = (c, m) => { console.log((c ? "PASS " : "FAIL ") + m); if (!c) fails++; };

function makeWorld(withLive = true) {
    const io = {
        "this_device audio_outputs 1": {
            types: [{ display_name: "No Output", identifier: 0 }, { display_name: "1-Audio", identifier: 11 }, { display_name: "Reverb Bus", identifier: 12 }],
            chans: { 0: [], 11: [{ display_name: "Track In", identifier: 1 }], 12: [{ display_name: "Track In", identifier: 1 }] },
            type: 0, chan: null,
        },
        "this_device audio_inputs 1": {
            types: [{ display_name: "No Input", identifier: 0 }, { display_name: "Reverb Bus", identifier: 12 }],
            chans: { 0: [], 12: [{ display_name: "Pre FX", identifier: 1 }, { display_name: "Post FX", identifier: 2 }, { display_name: "Post Mixer", identifier: 3 }] },
            type: 0, chan: null,
        },
    };
    const observers = [];
    const out = [[], [], [], []];
    let pending = [];
    class LiveAPI {
        constructor(a, b) {
            this.cb = typeof a === "function" ? a : null;
            this.path = typeof a === "function" ? b : a;
            this.id = withLive && io[this.path] ? "5" : "0";
            if (this.cb) observers.push(this);
        }
        get(p) {
            const s = io[this.path];
            const t = s.types.find(x => x.identifier === s.type);
            const chs = s.chans[s.type] || [];
            const c = chs.find(x => x.identifier === s.chan) || chs[0] || {};
            const v = { routing_type: t, routing_channel: c, available_routing_types: s.types, available_routing_channels: chs }[p];
            return [JSON.stringify({ [p]: v })];
        }
        set(p, val) {
            const o = typeof val === "string" ? JSON.parse(val) : val;
            const s = io[this.path];
            if (p === "routing_type") { s.type = o.identifier; s.chan = (s.chans[s.type][0] || {}).identifier; }
            else s.chan = o.identifier;
            observers.filter(w => w.path === this.path).forEach(w => pending.push(w.cb));
        }
    }
    class Task { constructor(f) { this.f = f; } cancel() {} schedule() { pending.push(this.f); } }
    const ctx = { LiveAPI, Task, outlet: (n, ...a) => out[n].push(a), autowatch: 0, inlets: 0, outlets: 0 };
    const fn = new Function(...Object.keys(ctx), code + "\nreturn {init, bang, sendtype, sendchan, rettype, retchan};");
    const api = fn(...Object.values(ctx));
    const flush = () => { while (pending.length) pending.shift()(); };
    const menu = n => { const items = []; let sel = null; for (const m of out[n]) { if (m[0] === "clear") items.length = 0; if (m[0] === "append") items.push(m[1]); if (m[0] === "set") sel = m[1]; } return { items, sel, cur: items[sel] }; };
    return { io, api, flush, menu, out };
}

let w = makeWorld();
w.api.bang(); w.flush();
ok(JSON.stringify(w.menu(0).items) === JSON.stringify(["No Output", "1-Audio", "Reverb Bus"]), "SEND track menu lists Live's routing types");
ok(w.menu(0).cur === "No Output", "SEND menu shows the current routing");
ok(JSON.stringify(w.menu(2).items) === JSON.stringify(["No Input", "Reverb Bus"]), "RETURN track menu lists Live's routing types");
w.api.sendtype(2); w.flush();
ok(w.io["this_device audio_outputs 1"].type === 12, "choosing 'Reverb Bus' sets the SEND routing_type");
ok(w.menu(0).cur === "Reverb Bus" && w.menu(1).cur === "Track In", "menus follow the new routing (track + channel)");
w.api.rettype(1); w.flush(); w.api.retchan(1); w.flush();
ok(w.io["this_device audio_inputs 1"].type === 12 && w.io["this_device audio_inputs 1"].chan === 2, "RETURN set to Reverb Bus / Post FX");
ok(w.menu(3).cur === "Post FX", "RETURN channel menu shows Post FX");
// external change (e.g. made in Live's own choosers) is followed
w.io["this_device audio_outputs 1"].type = 11; w.io["this_device audio_outputs 1"].chan = 1;
w.api.init(); w.flush();
ok(w.menu(0).cur === "1-Audio", "external routing change is reflected after a refresh");
// init is idempotent (live.thisdevice bangs again on preset load / save)
const nObs = w.out[0].length; w.api.bang(); w.flush();
ok(w.menu(0).cur === "1-Audio", "re-init keeps the routing (no reset on preset load)");
// no Live (e.g. opened in Max without Live)
let w2 = makeWorld(false);
w2.api.bang(); w2.flush();
ok(w2.menu(0).cur === "(needs Live 12.2+)", "without the Live API the menus say so and nothing is set");
console.log(fails ? `${fails} FAILED` : "ALL PASS");
process.exit(fails ? 1 : 0);

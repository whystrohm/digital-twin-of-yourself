#!/usr/bin/env python3
"""The README film: one object carries the story from files to score to drift
to a checked draft. Every number and sentence on screen comes from real
twin_scan and twin_check output on the synthetic sample.

build_page(data) returns an HTML page with a deterministic render(t) function
(t in seconds). make_demo.py screenshots it frame by frame.

Style follows the WhyStrohm film lock: ground, ink and one signal colour;
copy left, object right; two easings; headline words rise one at a time;
text waits for objects to land; no empty frames. Grain, the drifting grid
and the camera push are left out because they defeat GIF compression.
"""

import html
import json

W, H = 1920, 1080
START = 0.55      # the first frame is already in motion: never open on black
DURATION = 19.8   # seconds of film rendered, from START


def build_data(patterns, check, draft_line, fixed_line):
    c = patterns["corpora"][0]
    files = [f["file"] for f in c["files"]]
    hedge = {f["file"]: f["hedge_rate"] for f in c["files"]}
    drifting = [f["file"] for f in c["drift"]["files"] if f["drifting"]]
    worst = max(c["files"], key=lambda f: f["hedge_rate"])
    others = [f["hedge_rate"] for f in c["files"] if f["file"] != worst["file"]]
    res = {r["id"]: r for r in check["results"]}
    hits = []
    for rid in ("no-hedges", "no-dashes"):
        for h in res[rid]["hits"]:
            hits.append({"col": h["column"], "text": h["match"], "rule": rid})
    hits.sort(key=lambda h: h["col"])
    long_hit = res["sentence-length"]["hits"][0]["match"] if res["sentence-length"]["hits"] else ""
    return {
        "files": files,
        "words": c["totals"]["words"],
        "score": c["score"]["value"],
        "clean": c["score"]["parts"]["clean_lines"],
        "consistency": c["score"]["parts"]["consistency"],
        "clean_note": "%d of %d sentences carry no flag" % (
            c["totals"]["sentences"] - c["flags"]["flagged_sentences"], c["totals"]["sentences"]),
        "hist": c["sentence_length"]["histogram"],
        "long_words": patterns["settings"]["long_words"],
        "short_share": c["sentence_length"]["short_share"],
        "median": c["sentence_length"]["median"],
        "longest": c["sentence_length"]["max"],
        "hedge": hedge,
        "worst": worst["file"],
        "worst_rate": worst["hedge_rate"],
        "others_max": max(others) if others else 0,
        "drifting": drifting,
        "draft": draft_line,
        "fixed": fixed_line,
        "hits": hits,
        "rules": [
            {"id": "no-hedges", "label": "%d hedges" % len(res["no-hedges"]["hits"]), "ok": "0 hedges"},
            {"id": "no-dashes", "label": "%d dash" % len(res["no-dashes"]["hits"]), "ok": "0 dashes"},
            {"id": "sentence-length", "label": long_hit,
             "ok": "all under %s words" % res["sentence-length"]["limit"]},
        ],
    }


def _copy(d):
    pct = lambda x: "%d%%" % round(100 * x)
    over = sum(b["count"] for b in d["hist"] if int(b["label"].split("-")[0].rstrip("+")) > d["long_words"])
    return [
        {"at": 0.15, "out": 2.85, "eyebrow": "01 / Measure",
         "lines": ["Point it at", "your writing."], "signal": "writing.",
         "support": "%d files, %s words. Counted on your machine. Nothing is uploaded." % (
             len(d["files"]), "{:,}".format(d["words"]))},
        {"at": 3.05, "out": 6.15, "eyebrow": "02 / Score",
         "lines": ["Your voice,", "measured."], "signal": "measured.",
         "support": "%s clean lines. %s consistent from file to file." % (pct(d["clean"]), pct(d["consistency"]))},
        {"at": 6.3, "out": 9.65, "eyebrow": "03 / Rhythm",
         "lines": ["Short sentences,", "mostly."], "signal": "mostly.",
         "support": "%s run 8 words or fewer. %d run past 40." % (pct(d["short_share"]), over)},
        {"at": 9.85, "out": 13.65, "eyebrow": "04 / Drift",
         "lines": ["One file sounds", "like someone else."], "signal": "else.",
         "support": "%s hedges in %s of its sentences. The other files: %s." % (
             d["worst"], pct(d["worst_rate"]), pct(d["others_max"]))},
        {"at": 13.85, "out": 17.6, "eyebrow": "05 / Check",
         "lines": ["Every draft,", "checked."], "signal": "checked.",
         "support": "Against your own rules, line by line. Fix it, run it again."},
        {"at": 17.8, "out": 99, "eyebrow": "Open source / Runs offline",
         "lines": ["Digital Twin", "of Yourself."], "signal": "Yourself.",
         "support": ""},
    ]


def _draft_html(text, hits):
    out = []
    pos = 0
    for i, h in enumerate(hits):
        start = h["col"] - 1
        out.append(html.escape(text[pos:start]))
        out.append('<span class="hit" data-i="%d">%s</span>' % (i, html.escape(text[start:start + len(h["text"])])))
        pos = start + len(h["text"])
    out.append(html.escape(text[pos:]))
    return "".join(out)


CSS = """
html,body{margin:0;background:#07080A}
#stage{position:relative;width:1920px;height:1080px;overflow:hidden;background:#07080A;color:#F6F5F2;
font-family:"Archivo",Arial,sans-serif;
background-image:linear-gradient(rgba(246,245,242,.035) 1px,transparent 1px),
linear-gradient(90deg,rgba(246,245,242,.035) 1px,transparent 1px);background-size:80px 80px;background-position:-1px -1px}
#vig{position:absolute;inset:0;background:radial-gradient(ellipse at 60% 50%,transparent 45%,rgba(7,8,10,.85) 100%);pointer-events:none}
.abs{position:absolute;left:0;top:0;will-change:transform,opacity}
.copy{position:absolute;left:120px;top:300px;width:760px}
.eyebrow{font:500 26px "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.18em;text-transform:uppercase;color:rgba(246,245,242,.46)}
.hl{margin:26px 0 0;font-weight:700;font-size:104px;line-height:1.04;font-stretch:80%;letter-spacing:-.022em}
.hl .ln{display:block;white-space:nowrap}
.hl .w{display:inline-block;margin-right:.24em}
.hl .w.sig{color:#E4552A}
.sup{margin-top:34px;font-size:40px;line-height:1.3;font-weight:500;font-stretch:104%;color:rgba(246,245,242,.72);max-width:740px}
.card{border-radius:12px;background:rgba(246,245,242,.04);border:1.5px solid rgba(246,245,242,.16);box-sizing:border-box;overflow:hidden}
.card .nm{font:500 17px "IBM Plex Mono",ui-monospace,monospace;color:rgba(246,245,242,.72);padding:16px 18px 10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card .tl{height:9px;border-radius:5px;background:rgba(246,245,242,.16);margin:13px 18px 0;transform-origin:0 50%}
.panel{border-radius:16px;background:rgba(246,245,242,.04);border:1.5px solid rgba(246,245,242,.16);box-sizing:border-box}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace}
.big{font-weight:800;font-size:300px;line-height:.8;font-stretch:78%;letter-spacing:-.04em}
.of{font-size:64px;color:rgba(246,245,242,.46);font-weight:600;margin-left:12px}
.lab{font-size:28px;font-weight:500}
.val{font:500 24px "IBM Plex Mono",ui-monospace,monospace;color:rgba(246,245,242,.72)}
.track{height:14px;border-radius:7px;background:rgba(246,245,242,.12);overflow:hidden}
.fill{height:100%;background:rgba(246,245,242,.72);transform-origin:0 50%;border-radius:7px}
.note{font:500 22px "IBM Plex Mono",ui-monospace,monospace;color:rgba(246,245,242,.46);white-space:pre}
.bar{border-radius:8px 8px 0 0;background:rgba(246,245,242,.72);transform-origin:50% 100%}
.bar.sig{background:#E4552A}
.cl{font:500 22px "IBM Plex Mono",ui-monospace,monospace;color:rgba(246,245,242,.46);text-align:center}
.cnt{font:500 28px "IBM Plex Mono",ui-monospace,monospace;color:rgba(246,245,242,.72);text-align:center}
.dot{border-radius:50%;background:rgba(246,245,242,.72)}
.fname{font:500 24px "IBM Plex Mono",ui-monospace,monospace;color:rgba(246,245,242,.72);white-space:nowrap}
.tag{font:500 18px "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.12em;border:1.5px solid #E4552A;padding:3px 10px;border-radius:4px}
.axis{height:2px;background:rgba(246,245,242,.16);transform-origin:0 50%}
.draft{font-size:36px;line-height:1.42;font-weight:500;font-stretch:96%;color:#F6F5F2}
.draft .hi{color:rgba(246,245,242,.46)}
.hit{background:linear-gradient(#E4552A,#E4552A) no-repeat 0 100%/0% 4px;padding-bottom:2px}
.rule{display:flex;align-items:center;gap:18px;font:500 24px "IBM Plex Mono",ui-monospace,monospace;color:rgba(246,245,242,.72);height:44px}
.st{width:86px;font-weight:500;letter-spacing:.08em}
.st.f{color:#E4552A}.st.p{color:#F6F5F2}
.badge{font:500 30px "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.14em;padding:10px 22px;border-radius:8px;border:2px solid #E4552A;color:#E4552A}
.badge.p{border-color:#F6F5F2;color:#F6F5F2}
.btn{border-radius:48px;background:#E4552A;color:#07080A;display:flex;align-items:center;justify-content:center;
font:500 30px "IBM Plex Mono",ui-monospace,monospace;white-space:nowrap;overflow:hidden;letter-spacing:-.01em}
"""

JS = r"""
const D = __DATA__, COPY = __COPY__;
const $ = s => document.querySelector(s);
const stage = $('#stage');
function bez(s, a, b) { const u = 1 - s; return 3*a*s*u*u + 3*b*s*s*u + s*s*s; }
function cb(x1, y1, x2, y2) { return t => { if (t <= 0) return 0; if (t >= 1) return 1;
  let lo = 0, hi = 1, s = t; for (let i = 0; i < 30; i++) { s = (lo + hi) / 2; if (bez(s, x1, x2) < t) lo = s; else hi = s; }
  return bez(s, y1, y2); }; }
const ENTER = cb(.16, 1, .3, 1), MORPH = cb(.65, 0, .35, 1);
const cl = x => Math.max(0, Math.min(1, x));
const p = (t, a, d) => cl((t - a) / d);
const L = (a, b, k) => a + (b - a) * k;
function el(cls, parent, htmlText) { const e = document.createElement('div'); e.className = cls; if (htmlText !== undefined) e.innerHTML = htmlText; (parent || stage).appendChild(e); return e; }
function box(e, x, y, w, h, o, extra) { e.style.transform = `translate(${x}px,${y}px)` + (extra || ''); if (w !== null) e.style.width = w + 'px'; if (h !== null) e.style.height = h + 'px'; e.style.opacity = o; }

// ---------- copy
const copies = COPY.map(c => {
  const root = el('copy'); const eb = el('eyebrow', root, c.eyebrow);
  const hl = el('hl', root); const words = [];
  c.lines.forEach(line => { const ln = el('ln', hl); line.split(' ').forEach(w => {
    const s = document.createElement('span'); s.className = 'w' + (w === c.signal ? ' sig' : ''); s.textContent = w; ln.appendChild(s); words.push(s); }); });
  const sup = el('sup', root, c.support);
  return { c, root, eb, words, sup };
});
function drawCopy(t) {
  copies.forEach(({ c, root, eb, words, sup }) => {
    const out = 1 - p(t, c.out, 0.27);
    if (t < c.at - 0.01 || out <= 0) { root.style.opacity = 0; return; }
    root.style.opacity = 1;
    const a = ENTER(p(t, c.at, 0.47)); eb.style.opacity = a * out; eb.style.transform = `translateY(${(1-a)*16}px)`;
    words.forEach((w, i) => { const k = ENTER(p(t, c.at + 0.08 + i * 0.133, 0.47));
      w.style.opacity = k * out; w.style.transform = `translateY(${(1-k)*34}px)`; w.style.filter = `blur(${(1-k)*8}px)`; });
    const s = ENTER(p(t, c.at + 0.08 + words.length * 0.133 + 0.1, 0.5));
    sup.style.opacity = s * out; sup.style.transform = `translateY(${(1-s)*18}px)`;
  });
}

// ---------- geometry
const OX = 960, OY = 170, OW = 840, OH = 740;          // object area
const PANEL = { x: OX, y: OY + 40, w: OW, h: OH - 80 };

// step 1: file cards
const cards = D.files.map((f, i) => { const c = el('card abs'); el('nm', c, f);
  const lines = []; for (let j = 0; j < 7; j++) { const l = el('tl', c); l.style.width = (55 + ((i * 37 + j * 53) % 40)) + '%'; lines.push(l); }
  return { c, lines }; });
const CW = 190, CH = 250, GAP = 26;
function cardHome(i) { const row = i < 4 ? 0 : 1; const col = row ? i - 4 : i; const n = row ? 3 : 4;
  const rw = n * CW + (n - 1) * GAP; return { x: OX + (OW - rw) / 2 + col * (CW + GAP), y: OY + 90 + row * (CH + 44) }; }

// shared panel
const panel = el('panel abs');

// step 2: score
const scoreBox = el('abs'); scoreBox.style.display = 'flex'; scoreBox.style.alignItems = 'baseline';
const scoreNum = el('big', scoreBox); const ofEl = el('of', scoreBox, '/100');
const parts = [['Clean lines', D.clean], ['Consistency', D.consistency]].map(([name, v]) => {
  const lab = el('abs lab', null, name); const val = el('abs val', null, Math.round(v * 100) + '%');
  const tr = el('abs track'); const fl = el('fill', tr); return { lab, val, tr, fl, v }; });
const cleanNote = el('abs note');

// step 3: histogram
const HX = OX + 70, HW = OW - 140, HB = OY + OH - 150, HMAX = 360;
const peak = Math.max(...D.hist.map(b => b.count), 1);
const bars = D.hist.map((b, i) => { const lo = parseInt(b.label); const bar = el('abs bar' + (lo > D.long_words ? ' sig' : ''));
  const lab = el('abs cl', null, b.label); const cnt = el('abs cnt', null, String(b.count)); return { b, bar, lab, cnt }; });
const histLegend = el('abs note', null, 'sentences by length, in words');
const BW = (HW - 7 * 16) / 8;

// step 4: drift dots
const others = D.files.filter(f => f !== D.worst);
const AX = OX + 90, AW = OW - 180, AY = OY + 320;
const dots = D.files.map(f => ({ f, d: el('abs dot'), n: el('abs fname', null, f) }));
const axis = el('abs axis'); const axL = el('abs note', null, '0%'); const axR = el('abs note', null, '100%');
const axT = el('abs note', null, 'sentences with a hedge, per file');
const driftTag = el('abs tag', null, 'DRIFT'); const driftVal = el('abs val');
function dotHome(f) { const i = others.indexOf(f);
  if (i >= 0) return { x: AX, y: AY + 80 + i * 56 }; return { x: AX, y: AY - 70 }; }

// step 5: draft
const draftBox = el('abs draft'); const draftA = el('', draftBox, __DRAFT__); const draftB = el('', draftBox, __FIXED__);
draftB.style.position = 'absolute'; draftB.style.left = 0; draftB.style.top = 0;
const hitSpans = [...draftA.querySelectorAll('.hit')];
const rules = D.rules.map(r => { const row = el('abs rule'); const st = el('st f', row, 'FAIL'); el('', row, r.id); const n = el('', row, r.label);
  n.style.color = 'rgba(246,245,242,.46)'; return { row, st, n, r }; });
const badge = el('abs badge', null, 'FAIL'); const fileLab = el('abs note', null, 'examples/drafts/supplier-update.md');

// close
const btn = el('abs btn', null, 'github.com/whystrohm/digital-twin-of-yourself');

function hideAll(list) { list.forEach(e => e.style.opacity = 0); }

window.render = function (t) {
  drawCopy(t);
  // ---- step 1 cards: enter, then fly into the panel
  const fly = MORPH(p(t, 2.55, 0.8));
  cards.forEach(({ c, lines }, i) => { const h = cardHome(i); const a = ENTER(p(t, 0.1 + i * 0.12, 0.6));
    const cx = PANEL.x + PANEL.w / 2 - CW / 2, cy = PANEL.y + PANEL.h / 2 - CH / 2;
    const x = L(h.x, cx, fly), y = L(h.y + (1 - a) * 60, cy, fly), s = L(1, 0.35, fly);
    box(c, x, y, CW, CH, a * (1 - p(t, 3.05, 0.25)), ` scale(${s})`);
    lines.forEach((l, j) => { l.style.transform = `scaleX(${ENTER(p(t, 0.5 + i * 0.12 + j * 0.16, 0.5))})`; }); });

  // ---- panel: grows at 2.9, morphs to each step
  const R = [
    [2.9, { x: PANEL.x + PANEL.w / 2, y: PANEL.y + PANEL.h / 2, w: 0, h: 0 }],
    [3.5, PANEL],
    [13.65, PANEL],
    [14.3, { x: OX, y: OY + 60, w: OW, h: 620 }],
    [17.55, { x: OX, y: OY + 60, w: OW, h: 620 }],
    [18.25, { x: 120, y: 690, w: 900, h: 96 }],
  ];
  let rect = R[0][1], ro = 0;
  if (t >= R[0][0]) { ro = 1; for (let i = 0; i < R.length - 1; i++) { const [t0, a] = R[i], [t1, b] = R[i + 1];
    if (t >= t0) { const k = t >= t1 ? 1 : (i === 0 ? ENTER : MORPH)(p(t, t0, t1 - t0));
      rect = { x: L(a.x, b.x, k), y: L(a.y, b.y, k), w: L(a.w, b.w, k), h: L(a.h, b.h, k) }; } } }
  const toBtn = MORPH(p(t, 17.55, 0.7));
  box(panel, rect.x, rect.y, rect.w, rect.h, ro * (1 - p(t, 18.15, 0.12)));
  panel.style.background = `rgba(${Math.round(L(246, 228, toBtn))},${Math.round(L(245, 85, toBtn))},${Math.round(L(242, 42, toBtn))},${L(.04, 1, toBtn)})`;
  panel.style.borderRadius = L(16, 48, toBtn) + 'px';

  // ---- step 2 score
  const sIn = p(t, 3.5, 1.3), sOut = 1 - p(t, 6.05, 0.25);
  const n = Math.round(D.score * ENTER(sIn));
  scoreNum.textContent = t < 3.5 ? '0' : String(n);
  const sa = ENTER(p(t, 3.45, 0.4)) * sOut;
  box(scoreBox, PANEL.x + 70, PANEL.y + 90, null, null, sa);
  parts.forEach((q, i) => { const y = PANEL.y + 400 + i * 104, a = ENTER(p(t, 3.8 + i * 0.2, 0.45)) * sOut;
    box(q.lab, PANEL.x + 70, y, null, null, a); box(q.val, PANEL.x + PANEL.w - 150, y + 4, null, null, a);
    box(q.tr, PANEL.x + 70, y + 46, PANEL.w - 140, 14, a); q.fl.style.transform = `scaleX(${q.v * ENTER(p(t, 3.95 + i * 0.25, 1.0))})`; });
  const typed = Math.floor(D.clean_note.length * p(t, 5.0, 0.8));
  cleanNote.textContent = D.clean_note.slice(0, typed); box(cleanNote, PANEL.x + 70, PANEL.y + PANEL.h - 60, null, null, sOut);

  // ---- step 3 histogram
  const hOut = 1 - p(t, 9.6, 0.25);
  bars.forEach(({ b, bar, lab, cnt }, i) => { const x = HX + i * (BW + 16), full = HMAX * b.count / peak;
    const grow = ENTER(p(t, 6.45 + i * 0.09, 0.9)); const h = Math.max(full * grow, b.count ? 4 : 0);
    // bars become dots for the drift step: first collapse in place, then travel
    const tgt = i < D.files.length ? dotHome(D.files[i]) : null;
    const col = MORPH(p(t, 9.6, 0.35)), go = MORPH(p(t, 9.95, 0.55));
    if (t < 9.6) { box(bar, x, HB - h, BW, h, t < 6.45 ? 0 : 1); bar.style.borderRadius = '8px 8px 0 0'; }
    else if (!tgt) { box(bar, x, HB - h, BW, h, 1 - p(t, 9.6, 0.2)); }
    else { const cx = x + BW / 2, w = L(BW, 26, col), hh = L(h, 26, col);
      const px = L(cx - w / 2, tgt.x - 13, go), py = L(HB - hh, tgt.y - 13, go);
      box(bar, px, py, w, hh, 1 - p(t, 10.45, 0.1)); bar.style.borderRadius = L(8, 13, col) + 'px'; }
    const la = ENTER(p(t, 7.3 + i * 0.05, 0.4)) * hOut;
    box(lab, x - 10, HB + 16, BW + 20, null, la); box(cnt, x - 10, HB - h - 38, BW + 20, null, la); });
  box(histLegend, HX, PANEL.y + 40, null, null, ENTER(p(t, 7.6, 0.4)) * hOut);

  // ---- step 4 drift
  const dOut = 1 - p(t, 13.6, 0.25);
  const ax = ENTER(p(t, 10.15, 0.6));
  box(axis, AX, AY, AW, 2, (t >= 10.15 ? 1 : 0) * dOut, ` scaleX(${ax})`);
  box(axL, AX - 12, AY + 18, null, null, ax * dOut); box(axR, AX + AW - 48, AY + 18, null, null, ax * dOut);
  box(axT, AX, PANEL.y + 40, null, null, ENTER(p(t, 10.3, 0.4)) * dOut);
  const slide = MORPH(p(t, 10.9, 1.0));
  dots.forEach(({ f, d, n }) => { const h = dotHome(f); let x = h.x, y = h.y;
    const isW = f === D.worst;
    if (isW) { x = L(h.x, AX + AW * D.worst_rate, slide); y = AY; }
    const vis = (t >= 10.45 ? 1 : 0) * dOut;
    box(d, x - 13, y - 13, 26, 26, vis, isW ? ` scale(${1 + 0.4 * slide})` : '');
    d.style.background = isW && slide > 0.6 ? '#E4552A' : 'rgba(246,245,242,.72)';
    const la = isW ? ENTER(p(t, 11.95, 0.4)) : ENTER(p(t, 10.45 + others.indexOf(f) * 0.06, 0.4));
    box(n, isW ? x - 260 : x + 34, isW ? y - 70 : y - 17, null, null, la * dOut); });
  box(driftTag, AX + AW * D.worst_rate + 30, AY - 74, null, null, ENTER(p(t, 12.1, 0.35)) * dOut);
  const pc = Math.round(100 * D.worst_rate * ENTER(p(t, 12.1, 0.9)));
  driftVal.textContent = pc + '%'; box(driftVal, AX + AW * D.worst_rate - 34, AY + 30, null, null, ENTER(p(t, 12.1, 0.35)) * dOut);

  // ---- step 5 draft
  const fOut = 1 - p(t, 17.55, 0.15);
  const dx = OX + 60, dy = OY + 150;
  const dA = ENTER(p(t, 14.35, 0.5)) * fOut;
  box(draftBox, dx, dy + (1 - ENTER(p(t, 14.35, 0.5))) * 20, OW - 120, null, dA);
  box(fileLab, dx, OY + 70 + 18, null, null, dA);
  const outA = p(t, 15.9, 0.25), inB = ENTER(p(t, 16.15, 0.4));
  draftA.style.opacity = 1 - outA; draftB.style.opacity = inB; draftB.style.transform = `translateY(${(1 - inB) * 14}px)`;
  hitSpans.forEach((s, i) => { s.style.backgroundSize = `${100 * ENTER(p(t, 14.85 + i * 0.3, 0.35))}% 4px`; });
  rules.forEach(({ row, st, n, r }, i) => { const a = ENTER(p(t, 15.0 + i * 0.3, 0.35)) * fOut;
    box(row, dx, OY + 440 + i * 50, null, null, a);
    const ok = t >= 16.5 + i * 0.15; st.textContent = ok ? 'PASS' : 'FAIL'; st.className = 'st ' + (ok ? 'p' : 'f');
    n.textContent = ok ? r.ok : r.label; });
  const bOk = t >= 16.95; badge.textContent = bOk ? 'PASS' : 'FAIL'; badge.className = 'abs badge' + (bOk ? ' p' : '');
  box(badge, OX + OW - 200, OY + 450, null, null, ENTER(p(t, 15.85, 0.35)) * fOut);

  // ---- close
  const bt = p(t, 18.1, 0.2);
  box(btn, 120, 690, 900, 96, bt);
};
window.render(0);
"""


def build_page(data, font_css=""):
    copy = _copy(data)
    js = (JS.replace("__DATA__", json.dumps(data))
            .replace("__COPY__", json.dumps(copy))
            .replace("__DRAFT__", json.dumps(_draft_html(data["draft"], data["hits"])))
            .replace("__FIXED__", json.dumps(html.escape(data["fixed"]))))
    return ('<!doctype html><html><head><meta charset="utf-8"><style>%s%s</style></head><body>'
            '<div id="stage"><div id="vig"></div></div><script>%s</script></body></html>' % (font_css, CSS, js))

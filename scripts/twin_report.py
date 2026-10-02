#!/usr/bin/env python3
"""twin_report.py: turn patterns.json into one self-contained HTML file.

No external requests: no fonts, scripts, images or styles are fetched.
Charts are inline SVG. Light and dark themes. Every string is redacted
again (emails, phone numbers, money amounts) before it is written, and
excerpts are kept short.

Usage:
  python3 scripts/twin_report.py patterns.json --out twin-report.html
"""

import argparse
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import twinlib as tl  # noqa: E402

SNIPPET_MAX = 90
DRIFT_CAP = 6.0


def t(value):
    """Escape for HTML after redaction. Use for every piece of data."""
    return html.escape(tl.redact("" if value is None else str(value)), quote=True)


def short(value, width=SNIPPET_MAX):
    s = tl.redact("" if value is None else str(value))
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= width else s[: width - 3].rstrip() + "..."


def pct(x, places=0):
    return "n/a" if x is None else ("%." + str(places) + "f%%") % (100 * x)


def num(x, places=1):
    if x is None:
        return "n/a"
    if float(x).is_integer():
        return "{:,}".format(int(x))
    return ("{:,.%df}" % places).format(x)


# ---------------------------------------------------------------- charts


def bar_rows(rows, max_value, caption):
    """rows: dicts with label, value, display, note, flag. HTML rows, SVG bars."""
    if not rows:
        return '<p class="empty">Nothing to show.</p>'
    max_value = max_value or 1
    out = ['<div class="bars" role="list" aria-label="%s">' % t(caption)]
    for r in rows:
        w = max(0.0, min(100.0, 100.0 * r["value"] / max_value))
        cls = "bar flag" if r.get("flag") else "bar"
        tip = "%s: %s" % (r["label"], r["display"])
        out.append(
            '<div class="row" role="listitem">'
            '<div class="lab">%s%s</div><div class="val">%s</div>'
            '<svg class="%s" viewBox="0 0 100 10" preserveAspectRatio="none" aria-hidden="true">'
            '<title>%s</title>'
            '<rect class="track" x="0" y="0" width="100" height="10"/>'
            '<rect class="fill" x="0" y="0" width="%.2f" height="10"/>%s</svg>'
            '%s</div>' % (
                t(r["label"]),
                ' <span class="tag">%s</span>' % t(r["tag"]) if r.get("tag") else "",
                t(r["display"]), cls, t(tip), w,
                ('<line class="tick" x1="%.2f" x2="%.2f" y1="0" y2="10"/>' % (r["tick"], r["tick"]))
                if r.get("tick") is not None else "",
                '<div class="note">%s</div>' % t(r["note"]) if r.get("note") else "",
            ))
    out.append("</div>")
    return "\n".join(out)


def histogram(hist, long_words):
    peak = max((b["count"] for b in hist), default=0) or 1
    cols = []
    for b in hist:
        h = 100.0 * b["count"] / peak
        lo = int(b["label"].split("-")[0].rstrip("+"))
        over = lo > long_words
        cols.append(
            '<div class="col%s"><div class="cnt">%d</div>'
            '<svg viewBox="0 0 10 100" preserveAspectRatio="none" aria-hidden="true">'
            '<title>%s words: %d sentences</title>'
            '<rect class="fill" x="0" y="%.2f" width="10" height="%.2f"/></svg>'
            '<div class="cl">%s</div></div>' % (
                " flag" if over else "", b["count"], t(b["label"]), b["count"],
                100 - h, h, t(b["label"])))
    return ('<div class="hist" role="img" aria-label="Sentence length histogram">%s</div>'
            '<p class="legend"><span class="key"></span> sentence count by length in words'
            ' &nbsp; <span class="key flag"></span> over your long-sentence limit (%d)</p>'
            % ("".join(cols), long_words))


# ---------------------------------------------------------------- sections


def tiles(c):
    sl = c["sentence_length"]
    items = [
        ("Average sentence", "%s words" % num(sl["mean"])),
        ("Short sentences", pct(sl["short_share"])),
        ("Hedged sentences", pct(c["hedges"]["rate"], 1)),
        ("Questions", pct(c["questions"]["rate"], 1)),
        ("Dashes per 1k words", num(c["formatting"]["dash_per_1k"])),
        ("List lines", pct(c["formatting"]["list_line_share"])),
    ]
    return '<div class="tiles">%s</div>' % "".join(
        '<div class="tile"><div class="tv">%s</div><div class="tl">%s</div></div>' % (t(v), t(k))
        for k, v in items)


def section_score(c):
    s = c["score"]
    parts = s["parts"]
    rows = []
    if parts.get("clean_lines") is not None:
        rows.append({"label": "Clean lines", "value": parts["clean_lines"], "display": pct(parts["clean_lines"]),
                     "note": "%d of %d sentences carry no flag." % (
                         c["totals"]["sentences"] - c["flags"]["flagged_sentences"], c["totals"]["sentences"])})
    if parts.get("consistency") is not None:
        d = c["drift"]
        rows.append({"label": "Consistency", "value": parts["consistency"], "display": pct(parts["consistency"]),
                     "note": "%d of %d file and metric pairs sit inside your normal range." % (
                         d["total_pairs"] - d["flagged_pairs"], d["total_pairs"])})
    else:
        rows.append({"label": "Consistency", "value": 0, "display": "n/a",
                     "note": "Needs 3 or more files of %d+ words." % 40})
    value = "n/a" if s["value"] is None else str(s["value"])
    return (
        '<section id="%s-score" class="score">'
        '<div class="hero"><div class="eyebrow">Score</div>'
        '<div class="big">%s<span>/100</span></div>'
        '<p class="muted">Measured by code from your files. It shows how clean and how consistent the '
        'writing is. It is not a grade of quality.</p></div>'
        '<div class="parts">%s<p class="formula">%s</p></div></section>' % (
            t(c["name"]), t(value), bar_rows(rows, 1, "Score parts"), t(s["formula"])))


def section_repeats(c):
    cp = c["crutch_phrases"][:15]
    rows = [{"label": '"%s"' % p["phrase"], "value": p["count"], "display": "%dx" % p["count"],
             "note": "in %d file%s, first at %s:%d" % (p["files"], "" if p["files"] == 1 else "s",
                                                       p["first_seen"]["file"], p["first_seen"]["line"])}
            for p in cp]
    hedges = c["hedges"]["terms"][:10]
    hrows = [{"label": h["term"], "value": h["count"], "display": "%dx" % h["count"]}
             for h in hedges]
    meta = [m for m in c["metaphor_families"] if m["count"]]
    mrows = [{"label": m["family"], "value": m["per_1k"], "display": "%s per 1k" % num(m["per_1k"]),
              "note": ", ".join(m["top_words"])} for m in meta]
    return (
        '<section id="%s-repeats"><h2>Patterns you repeat</h2>'
        '<p class="muted">Phrases of 3 to 5 words used %d or more times, ranked by count.</p>%s'
        '<h3>Hedges</h3>%s'
        '<h3>Metaphor-family words</h3><p class="muted">Counted from a word list. A hit is a candidate, '
        'not a confirmed metaphor.</p>%s</section>' % (
            t(c["name"]), c.get("_min_repeat", 3),
            bar_rows(rows, max([5] + [r["value"] for r in rows]), "Repeated phrases")
            if rows else '<p class="empty">No phrase repeats often enough to list.</p>',
            bar_rows(hrows, max([5] + [r["value"] for r in hrows]), "Hedges")
            if hrows else '<p class="empty">No hedges found.</p>',
            bar_rows(mrows, max((r["value"] for r in mrows), default=1), "Metaphor families")
            if mrows else '<p class="empty">No metaphor-family words found.</p>'))


def section_drift(c):
    d = c["drift"]
    if d["eligible_files"] < 3:
        body = '<p class="empty">Drift needs 3 or more files of 40+ words. This corpus has %d.</p>' % d["eligible_files"]
        return '<section id="%s-drift"><h2>Where your voice drifts</h2>%s</section>' % (t(c["name"]), body)
    tick = 100.0 * d["threshold_z"] / DRIFT_CAP
    rows = []
    for f in d["files"]:
        z = f["max_abs_z"]
        worst = max(f["metrics"], key=lambda m: (abs(m["z"]), m["metric"]))
        rows.append({
            "label": f["file"], "value": min(z, DRIFT_CAP), "flag": bool(f["drifting"]),
            "display": "z %s%s" % (num(z, 1), "+" if z > DRIFT_CAP else ""),
            "tag": "drift" if f["drifting"] else None,
            "tick": tick,
            "note": ("%s: %s here, %s in the other files" % (
                worst["label"], num(worst["value"], 3), num(worst["others_mean"], 3))),
        })
    detail = []
    for f in d["files"]:
        for m in f["metrics"]:
            if m["drift"]:
                detail.append("<tr><td>%s</td><td>%s</td><td class=n>%s</td><td class=n>%s</td><td class=n>%s</td></tr>" % (
                    t(f["file"]), t(m["label"]), t(num(m["value"], 3)), t(num(m["others_mean"], 3)),
                    t("%+.1f" % m["z"])))
    table = ('<div class="tw"><table><thead><tr><th>File</th><th>Metric</th><th class=n>This file</th>'
             '<th class=n>Other files</th><th class=n>z</th></tr></thead><tbody>%s</tbody></table></div>'
             % "".join(detail)) if detail else '<p class="empty">No file sits outside its normal range.</p>'
    return (
        '<section id="%s-drift"><h2>Where your voice drifts</h2>'
        '<p class="muted">Each file against the other files. The bar is the largest gap in standard '
        'deviations; the tick marks %.1f, the drift line. Bars stop at %d.</p>%s'
        '<h3>What moved</h3>%s</section>' % (
            t(c["name"]), d["threshold_z"], int(DRIFT_CAP),
            bar_rows(rows, DRIFT_CAP, "Drift by file"), table))


def mark(snippet_text, match):
    s = t(short(snippet_text))
    if not match or match in ("dash",) or re.match(r"^\d+ words$", match):
        if match == "dash":
            return s.replace("\u2014", '<mark>\u2014</mark>').replace(" -- ", " <mark>--</mark> ")
        return s
    m = re.search(re.escape(t(match)), s, re.IGNORECASE)
    if not m:
        return s
    return s[: m.start()] + "<mark>" + s[m.start(): m.end()] + "</mark>" + s[m.end():]


def section_flags(c):
    fl = c["flags"]
    counts = fl["counts"]
    head = '<p class="muted">%d hedges, %d long sentences, %d dashes. Fixes are computed, not written by a model.</p>' % (
        counts["hedge"], counts["long_sentence"], counts["dash"])
    if not fl["items"]:
        return '<section id="%s-flags"><h2>Flagged lines</h2>%s<p class="empty">Nothing flagged.</p></section>' % (
            t(c["name"]), head)
    cards = []
    for f in fl["items"]:
        fix_label = "Fix" if f.get("fix_is_rewrite") else "Do"
        cards.append(
            '<li class="flagcard"><div class="where">%s:%d <span class="kind">%s</span></div>'
            '<div class="line">%s</div><div class="why">%s</div>'
            '<div class="fix"><span>%s</span> %s</div></li>' % (
                t(f["file"]), f["line"], t(f["kind"].replace("_", " ")),
                mark(f["snippet"], f.get("match")), t(f["why"]), fix_label, t(short(f["fix"]))))
    more = '<p class="muted">%d more not shown. Raise --max-flags to see them.</p>' % fl["truncated"] if fl["truncated"] else ""
    return '<section id="%s-flags"><h2>Flagged lines with a suggested fix</h2>%s<ol class="flags">%s</ol>%s</section>' % (
        t(c["name"]), head, "".join(cards), more)


def section_shape(c, long_words):
    sl = c["sentence_length"]
    f = c["formatting"]
    facts = [
        ("Median sentence", "%s words" % num(sl["median"])),
        ("90th percentile", "%s words" % num(sl["p90"])),
        ("Longest", "%s words" % num(sl["max"])),
        ("Short / medium / long", "%s / %s / %s" % (pct(sl["short_share"]), pct(sl["medium_share"]), pct(sl["long_share"]))),
        ("Headings", num(f["headings"])),
        ("Bold per 1k words", num(f["bold_per_1k"])),
        ("All-caps words per 1k", num(f["all_caps_per_1k"])),
        ("Exclamations", pct(c["exclamations"]["rate"], 1)),
        ("Emoji", num(f["emoji"])),
    ]
    dl = "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (t(k), t(v)) for k, v in facts)
    return ('<section id="%s-shape"><h2>Shape of the writing</h2>%s<dl class="facts">%s</dl></section>' % (
        t(c["name"]), histogram(sl["histogram"], long_words), dl))


def section_compare(cmp_):
    names = cmp_["corpora"]
    head = "".join("<th class=n>%s</th>" % t(n) for n in names)
    body = []
    for row in cmp_["table"]:
        cells = "".join("<td class=n>%s</td>" % t(num(row["values"][n], 3) if row["values"][n] is not None else "n/a")
                        for n in names)
        body.append("<tr><td>%s</td>%s</tr>" % (t(row["metric"].replace("_", " ")), cells))
    shared = ", ".join('"%s"' % p for p in cmp_["shared_phrases"]) or "none"
    only = "".join("<li><strong>%s</strong>: %s</li>" % (
        t(n), t(", ".join('"%s"' % p for p in ps[:8]) or "none")) for n, ps in sorted(cmp_["only_in"].items()))
    return ('<section id="compare"><h2>Across corpora</h2><div class="tw"><table><thead><tr><th>Metric</th>%s</tr>'
            '</thead><tbody>%s</tbody></table></div><h3>Repeated phrases</h3><p>Shared: %s</p><ul class="plain">%s</ul>'
            '</section>' % (head, "".join(body), t(shared), only))


# ---------------------------------------------------------------- page

CSS = """
:root{--bg:#07080A;--ink:#F6F5F2;--i66:rgba(246,245,242,.66);--i40:rgba(246,245,242,.40);
--i22:rgba(246,245,242,.22);--i08:rgba(246,245,242,.08);--sig:#E4552A;color-scheme:dark}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]){--bg:#F6F5F2;--ink:#07080A;
--i66:rgba(7,8,10,.66);--i40:rgba(7,8,10,.40);--i22:rgba(7,8,10,.22);--i08:rgba(7,8,10,.08);color-scheme:light}}
:root[data-theme="light"]{--bg:#F6F5F2;--ink:#07080A;--i66:rgba(7,8,10,.66);--i40:rgba(7,8,10,.40);
--i22:rgba(7,8,10,.22);--i08:rgba(7,8,10,.08);color-scheme:light}
*{box-sizing:border-box}html,body{margin:0}
body{background:var(--bg);color:var(--ink);font:16px/1.5 "Archivo","Helvetica Neue",Arial,sans-serif;
-webkit-font-smoothing:antialiased}
.mono,.eyebrow,.val,.tag,.where,.cnt,.cl,.tv,dd,td.n,th.n,.formula,.note,.kind,.fix span,nav a{
font-family:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace}
.wrap{max-width:1040px;margin:0 auto;padding:40px 16px 64px}
header{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;border-bottom:1px solid var(--i22);padding-bottom:20px}
h1{font-size:clamp(32px,6vw,56px);line-height:1;margin:8px 0 10px;font-weight:800;letter-spacing:-.02em;font-stretch:85%}
h2{font-size:clamp(22px,3.4vw,30px);margin:56px 0 6px;font-weight:800;letter-spacing:-.01em;font-stretch:90%}
h3{font-size:15px;margin:28px 0 8px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--i66)}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--i66)}
.muted,.empty{color:var(--i66);margin:4px 0 16px;max-width:68ch}
.meta{color:var(--i66);font-size:14px;margin:0}
button.theme{background:none;border:1px solid var(--i40);color:var(--ink);font:12px "IBM Plex Mono",ui-monospace,monospace;
padding:8px 12px;cursor:pointer;letter-spacing:.08em;text-transform:uppercase;min-height:36px}
button.theme:hover{border-color:var(--ink)}
nav{display:flex;flex-wrap:wrap;gap:8px 18px;margin:18px 0 0}nav a{color:var(--i66);font-size:12px;text-decoration:none;
letter-spacing:.08em;text-transform:uppercase}nav a:hover{color:var(--ink)}
.score{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.4fr);gap:32px;margin-top:36px;align-items:start}
.big{font-size:clamp(88px,16vw,148px);font-weight:800;line-height:.9;letter-spacing:-.04em;font-stretch:80%}
.big span{font-size:.24em;color:var(--i66);letter-spacing:0;margin-left:6px;font-weight:600}
.formula{font-size:12px;color:var(--i40);margin-top:14px}
.tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--i22);border:1px solid var(--i22);margin:28px 0 0}
.tile{background:var(--bg);padding:14px 16px}.tv{font-size:22px}.tl{font-size:13px;color:var(--i66)}
.bars{display:flex;flex-direction:column;gap:14px}
.row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 12px;align-items:baseline}
.lab{min-width:0;overflow-wrap:anywhere}.val{font-size:13px;color:var(--i66);text-align:right}
.row svg{grid-column:1/-1;width:100%;height:10px;display:block;border-radius:0 4px 4px 0;overflow:hidden}
.track{fill:var(--i08)}.fill{fill:var(--i66)}.bar.flag .fill{fill:var(--sig)}
.tick{stroke:var(--ink);stroke-width:1.5;vector-effect:non-scaling-stroke}
.note{grid-column:1/-1;font-size:12px;color:var(--i40)}
.tag{font-size:11px;border:1px solid var(--sig);color:var(--ink);padding:0 6px;margin-left:6px;letter-spacing:.06em;text-transform:uppercase}
.hist{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:2px;align-items:end;height:200px;margin-top:12px}
.col{display:flex;flex-direction:column;justify-content:flex-end;height:100%;text-align:center}
.col svg{width:100%;height:150px;display:block}.col .fill{fill:var(--i66)}.col.flag .fill{fill:var(--sig)}
.cnt{font-size:12px;color:var(--i66)}.cl{font-size:11px;color:var(--i40);margin-top:6px}
.legend{font-size:12px;color:var(--i66);margin-top:12px}.key{display:inline-block;width:10px;height:10px;background:var(--i66);vertical-align:-1px}
.key.flag{background:var(--sig)}
.tw{overflow-x:auto;border:1px solid var(--i22)}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--i22);vertical-align:top}
th{font-weight:600;color:var(--i66);font-size:12px;text-transform:uppercase;letter-spacing:.06em}.n{text-align:right;white-space:nowrap}
tbody tr:last-child td{border-bottom:0}
ol.flags{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:1px;background:var(--i22);border:1px solid var(--i22)}
.flagcard{background:var(--bg);padding:14px 16px}
.where{font-size:12px;color:var(--i66)}.kind{color:var(--ink);border-left:2px solid var(--sig);padding-left:6px;margin-left:8px}
.line{margin:6px 0 4px;overflow-wrap:anywhere}.why{font-size:14px;color:var(--i66)}
.fix{font-size:14px;margin-top:6px;overflow-wrap:anywhere}.fix span{font-size:11px;color:var(--i66);text-transform:uppercase;letter-spacing:.1em;margin-right:6px}
mark{background:none;color:var(--ink);border-bottom:2px solid var(--sig)}
dl.facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--i22);border:1px solid var(--i22);margin:24px 0 0}
dl.facts div{background:var(--bg);padding:12px 14px}dt{font-size:13px;color:var(--i66)}dd{margin:2px 0 0;font-size:17px}
ul.plain{padding-left:18px}
.corpus{margin-top:20px}.corpus+.corpus,#compare+.corpus{border-top:1px solid var(--i22);margin-top:48px;padding-top:8px}
footer{margin-top:64px;border-top:1px solid var(--i22);padding-top:16px;font-size:13px;color:var(--i40)}
@media (max-width:720px){.score{grid-template-columns:1fr;gap:12px}.tiles,dl.facts{grid-template-columns:repeat(2,minmax(0,1fr))}
.wrap{padding-top:24px}header{flex-direction:column-reverse}.hist{height:170px}.col svg{height:120px}}
"""

JS = """
(function(){var r=document.documentElement,b=document.getElementById('theme');
function cur(){return r.getAttribute('data-theme')||(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark')}
function label(){b.textContent=cur()==='dark'?'Light':'Dark'}
try{var s=localStorage.getItem('twin-theme');if(s)r.setAttribute('data-theme',s)}catch(e){}
label();b.addEventListener('click',function(){var n=cur()==='dark'?'light':'dark';r.setAttribute('data-theme',n);
try{localStorage.setItem('twin-theme',n)}catch(e){}label()})})();
"""


def render(data, title=None):
    corpora = data["corpora"]
    long_words = data["settings"].get("long_words", 30)
    for c in corpora:
        c["_min_repeat"] = data["settings"].get("min_repeat", 3)
    name = title or (corpora[0]["name"] if len(corpora) == 1 else "%d corpora" % len(corpora))
    parts = []
    for c in corpora:
        tot = c["totals"]
        red = c["redactions"]
        anchor = t(c["name"])
        nav = "".join('<a href="#%s-%s">%s</a>' % (anchor, k, v) for k, v in (
            ("score", "Score"), ("repeats", "Repeats"), ("drift", "Drift"), ("flags", "Flagged lines"), ("shape", "Shape")))
        parts.append(
            '<div class="corpus">%s<p class="meta mono">%s files &middot; %s words &middot; %s sentences &middot; redacted before analysis: '
            '%d email, %d phone, %d amount</p><nav>%s</nav>%s%s%s%s%s%s</div>' % (
                ('<div class="eyebrow">Corpus</div><h2 style="margin-top:6px">%s</h2>' % anchor)
                if len(corpora) > 1 else "", num(tot["files"]), num(tot["words"]), num(tot["sentences"]),
                red["email"], red["phone"], red["amount"], nav,
                section_score(c), tiles(c), section_repeats(c), section_drift(c), section_flags(c),
                section_shape(c, long_words)))
    compare = section_compare(data["comparison"]) if data.get("comparison") else ""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Twin Report</title><style>%s</style></head><body><div class="wrap">'
        '<header><div><div class="eyebrow">Twin report</div><h1>%s</h1>'
        '<p class="meta">Patterns measured by code from your own files. Snippets are short and redacted.</p></div>'
        '<button class="theme" id="theme" type="button" aria-label="Switch colour theme">Light</button></header>'
        '%s%s<footer>Generated by twin_report.py from %s (schema %s v%s). This file makes no network requests. '
        'Emails, phone numbers and money amounts are redacted.</footer></div><script>%s</script></body></html>\n' % (
            CSS, t(name), compare, "".join(parts), t(data.get("tool", "twin_scan.py")),
            t(data.get("schema")), t(data.get("version")), JS))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("patterns", help="patterns.json from twin_scan.py")
    ap.add_argument("--out", default="twin-report.html")
    ap.add_argument("--title", help="heading for the report")
    args = ap.parse_args(argv)
    try:
        data = tl.load_json(args.patterns)
    except (OSError, ValueError) as exc:
        print("twin_report: cannot read %s: %s" % (args.patterns, exc), file=sys.stderr)
        return 2
    if data.get("schema") != "twin-patterns" or not data.get("corpora"):
        print("twin_report: %s is not a twin_scan patterns file" % args.patterns, file=sys.stderr)
        return 2
    page = render(data, args.title)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("wrote %s (%d KB, no external requests)" % (args.out, (len(page.encode("utf-8")) + 1023) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""A designed still of what the report shows, in the same system as the
diagram: eyebrow, headline, then four large panels. Every value comes from
the real patterns.json of the synthetic sample.

make_demo.py renders it to assets/report.png. Palette only.
"""

import html
import re

W, H = 1200, 740


def _esc(s):
    return html.escape(str(s))


def page(patterns, font_css=""):
    c = patterns["corpora"][0]
    score = c["score"]
    parts = score["parts"]
    phrases = c["crutch_phrases"][:3]
    top = max([p["count"] for p in phrases] + [1])
    files = c["files"]
    worst = max(files, key=lambda f: f["hedge_rate"])
    rest = [f for f in files if f["file"] != worst["file"]]
    rest_max = max([f["hedge_rate"] for f in rest] + [0])
    flag = next(f for f in c["flags"]["items"] if f["kind"] == "hedge")

    def bar(label, value, display, sig=False):
        return ('<div class="row"><div class="rl">%s</div><div class="rv">%s</div>'
                '<div class="tr"><div class="fl%s" style="width:%.1f%%"></div></div></div>' % (
                    _esc(label), _esc(display), " sig" if sig else "", 100 * value))

    score_panel = (
        '<div class="p"><div class="pl">Score</div>'
        '<div class="sc"><span class="n">%s</span><span class="of">/100</span></div>%s%s</div>' % (
            _esc(score["value"]),
            bar("Clean lines", parts["clean_lines"], "%d%%" % round(100 * parts["clean_lines"])),
            bar("Consistency", parts["consistency"], "%d%%" % round(100 * parts["consistency"]))))

    rep_panel = '<div class="p"><div class="pl">Phrases you repeat</div>%s</div>' % "".join(
        bar('"%s"' % p["phrase"], p["count"] / top, "%dx" % p["count"]) for p in phrases)

    pos = 100 * worst["hedge_rate"]
    drift_panel = (
        '<div class="p"><div class="pl">Where your voice drifts</div>'
        '<div class="dz">'
        '<div class="ax"></div><div class="t0">0%%</div><div class="t1">100%%</div>'
        '<div class="dot one"></div>'
        '<div class="dot sig" style="left:%.1f%%"></div>'
        '<div class="dl" style="left:%.1f%%">%s <span class="tag">DRIFT</span></div>'
        '<div class="dv" style="left:%.1f%%">%d%%</div>'
        '<div class="cl">%d other files, %d%%</div>'
        '</div><div class="cap">Sentences with a hedge, per file</div></div>' % (
            pos, pos, _esc(worst["file"]), pos,
            round(pos), len(rest), round(100 * rest_max)))

    snippet = _esc(flag["snippet"])
    m = re.search(re.escape(_esc(flag["match"])), snippet, re.IGNORECASE)
    if m:
        snippet = snippet[:m.start()] + "<mark>" + snippet[m.start():m.end()] + "</mark>" + snippet[m.end():]
    flag_panel = (
        '<div class="p"><div class="pl">Flagged lines, with a fix</div>'
        '<div class="where">%s:%d <span class="kind">hedge</span></div>'
        '<div class="ln">%s</div><div class="why">%s</div>'
        '<div class="fix"><span>FIX</span>%s</div></div>' % (
            _esc(flag["file"]), flag["line"], snippet, _esc(flag["why"]), _esc(flag["fix"])))

    css = """
html,body{margin:0;background:#07080A}
body{width:%dpx;height:%dpx;overflow:hidden;color:#F6F5F2;font-family:"Archivo",Arial,sans-serif}
.eb{position:absolute;left:40px;top:44px;font:500 13px "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.16em;color:#E4552A}
.ti{position:absolute;left:40px;top:66px;font-weight:800;font-size:32px;font-stretch:85%%;letter-spacing:-.01em}
.sub{position:absolute;left:760px;top:52px;width:400px;font-size:14px;line-height:1.45;color:rgba(246,245,242,.66)}
.rule{position:absolute;left:40px;right:40px;top:124px;height:1px;background:rgba(246,245,242,.22)}
.grid{position:absolute;left:40px;top:150px;width:1120px;display:grid;grid-template-columns:1fr 1fr;gap:20px}
.p{height:270px;box-sizing:border-box;padding:24px 28px;border:1px solid rgba(246,245,242,.22);border-radius:4px;
background:rgba(246,245,242,.03);position:relative;overflow:hidden}
.pl{font:500 12px "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.16em;text-transform:uppercase;color:rgba(246,245,242,.66);margin-bottom:16px}
.sc{display:flex;align-items:baseline;margin:-6px 0 14px}
.n{font-weight:800;font-size:104px;line-height:.9;font-stretch:78%%;letter-spacing:-.04em}
.of{font-size:26px;color:rgba(246,245,242,.46);font-weight:600;margin-left:8px}
.row{display:grid;grid-template-columns:1fr auto;gap:6px 12px;margin-bottom:16px}
.rl{font-size:17px}.rv{font:500 14px "IBM Plex Mono",ui-monospace,monospace;color:rgba(246,245,242,.66)}
.tr{grid-column:1/-1;height:10px;border-radius:5px;background:rgba(246,245,242,.08);overflow:hidden}
.fl{height:100%%;border-radius:5px;background:rgba(246,245,242,.66)}.fl.sig{background:#E4552A}
.dz{position:relative;height:150px;margin:22px 14px 0}
.ax{position:absolute;left:0;right:0;top:90px;height:2px;background:rgba(246,245,242,.22)}
.t0,.t1{position:absolute;top:104px;font:500 12px "IBM Plex Mono",ui-monospace,monospace;color:rgba(246,245,242,.46)}
.t0{left:-6px}.t1{right:-12px}
.dot{width:16px;height:16px;border-radius:50%%;background:rgba(246,245,242,.66);box-shadow:0 0 0 3px #0c0d0f}
.dot.one{position:absolute;left:0;top:81px;width:20px;height:20px;transform:translateX(-10px)}
.dot.sig{position:absolute;top:80px;width:22px;height:22px;background:#E4552A;transform:translateX(-11px)}
.dl{position:absolute;top:36px;transform:translateX(-50%%);font:500 15px "IBM Plex Mono",ui-monospace,monospace;white-space:nowrap}
.dv{position:absolute;top:110px;transform:translateX(-50%%);font:500 15px "IBM Plex Mono",ui-monospace,monospace;color:#F6F5F2}
.cl{position:absolute;left:-10px;top:42px;font:500 15px "IBM Plex Mono",ui-monospace,monospace;color:rgba(246,245,242,.66);white-space:nowrap}
.tag{font-size:11px;letter-spacing:.12em;border:1px solid #E4552A;padding:1px 6px;margin-left:6px;border-radius:2px}
.cap{position:absolute;left:28px;bottom:22px;font-size:14px;color:rgba(246,245,242,.46)}
.where{font:500 13px "IBM Plex Mono",ui-monospace,monospace;color:rgba(246,245,242,.66)}
.kind{color:#F6F5F2;border-left:2px solid #E4552A;padding-left:6px;margin-left:8px}
.ln{font-size:21px;line-height:1.35;margin:10px 0 8px}
mark{background:none;color:#F6F5F2;border-bottom:3px solid #E4552A}
.why{font-size:15px;color:rgba(246,245,242,.66)}
.fix{font-size:16px;margin-top:14px;line-height:1.4}
.fix span{font:500 12px "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.12em;color:rgba(246,245,242,.66);margin-right:10px}
""" % (W, H)
    body = (
        '<div class="eb">THE REPORT</div><div class="ti">One page, built from your own files.</div>'
        '<div class="sub">Opens in any browser, light or dark. No network requests. '
        'Emails, phone numbers and money amounts are redacted.</div><div class="rule"></div>'
        '<div class="grid">%s%s%s%s</div>' % (score_panel, rep_panel, drift_panel, flag_panel))
    return '<!doctype html><html><head><meta charset="utf-8"><style>%s%s</style></head><body>%s</body></html>' % (
        font_css, css, body)

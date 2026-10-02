#!/usr/bin/env python3
"""Build assets/demo.gif and assets/hero.png from real runs.

Dev-only. Not needed to use the twin scripts. Needs:
  - Python with Playwright (pip install playwright) and Google Chrome or a
    Playwright Chromium
  - ffmpeg on PATH
  - optional: --font-dir holding Archivo-VF.ttf and IBMPlexMono-Regular.ttf
    (both SIL OFL). They are injected into the captured pages only; the
    shipped report never loads fonts.

What it does, in order:
  1. Copies scripts/, examples/ and twins/ into a temp folder.
  2. Runs twin_scan.py, twin_report.py and twin_check.py there and captures
     their stdout exactly.
  3. Renders each command and its output as a terminal page, screenshots it,
     and screenshots the real report it produced.
  4. Stitches the screenshots into a GIF (under 20 seconds) with ffmpeg.

Every number and line in the GIF comes from those runs on the synthetic
sample in examples/. Nothing is typed in by hand.

  python tools/demo/make_demo.py --font-dir /path/to/fonts
"""

import argparse
import html
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W, H = 1200, 750

TERM_CSS = """
html,body{margin:0;background:#07080A}
body{width:%dpx;height:%dpx;overflow:hidden;color:#F6F5F2;font:14px/1.5 "IBM Plex Mono",ui-monospace,Menlo,monospace}
.bar{height:40px;border-bottom:1px solid rgba(246,245,242,.22);display:flex;align-items:center;padding:0 24px;
color:rgba(246,245,242,.66);font-size:12px;letter-spacing:.12em;text-transform:uppercase;justify-content:space-between}
.bar b{color:#F6F5F2;font-weight:400}
.step{color:#E4552A}
pre{margin:0;padding:22px 24px;white-space:pre-wrap;word-break:break-word}
.cmd{color:#F6F5F2}.cmd .p{color:#E4552A}.out{color:rgba(246,245,242,.66)}
.fail{color:#E4552A}.pass{color:#F6F5F2}
.add{color:#F6F5F2}.del{color:rgba(246,245,242,.40);text-decoration:line-through}
""" % (W, H)


def font_css(font_dir):
    if not font_dir:
        return ""
    return ('@font-face{font-family:"Archivo";src:url("file://%s/Archivo-VF.ttf");font-weight:100 900;'
            'font-stretch:62%% 125%%}@font-face{font-family:"IBM Plex Mono";'
            'src:url("file://%s/IBMPlexMono-Regular.ttf")}' % (font_dir, font_dir))


def run(cmd, cwd):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.stdout + proc.stderr, proc.returncode


def colour_line(line):
    e = html.escape(line)
    if line.startswith("FAIL") or line.startswith("result      FAIL"):
        return '<span class="fail">%s</span>' % e
    if line.startswith("PASS") or line.startswith("result      PASS"):
        return '<span class="pass">%s</span>' % e
    if line.startswith("+") and not line.startswith("+++"):
        return '<span class="add">%s</span>' % e
    if line.startswith("-") and not line.startswith("---"):
        return '<span class="del">%s</span>' % e
    return e


def terminal_page(step, label, blocks, fonts):
    body = []
    for cmd, out in blocks:
        body.append('<span class="cmd"><span class="p">$</span> %s</span>' % html.escape(cmd))
        if out:
            body.append('<span class="out">%s</span>' % "\n".join(colour_line(l) for l in out.rstrip("\n").split("\n")))
        body.append("")
    return ('<!doctype html><html><head><meta charset="utf-8"><style>%s%s</style></head><body>'
            '<div class="bar"><span><span class="step">%s</span> &nbsp; <b>%s</b></span>'
            '<span>synthetic sample data</span></div><pre>%s</pre></body></html>' % (
                font_css(fonts), TERM_CSS, html.escape(step), html.escape(label), "\n".join(body)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--font-dir")
    ap.add_argument("--out-gif", default=os.path.join(ROOT, "assets", "demo.gif"))
    ap.add_argument("--out-hero", default=os.path.join(ROOT, "assets", "hero.png"))
    ap.add_argument("--keep", action="store_true", help="keep the frames folder")
    args = ap.parse_args()
    fonts = os.path.abspath(args.font_dir) if args.font_dir else None

    from playwright.sync_api import sync_playwright

    work = tempfile.mkdtemp(prefix="twin-demo-")
    repo = os.path.join(work, "digital-twin-of-yourself")
    frames = os.path.join(work, "frames")
    os.makedirs(frames)
    for d in ("scripts", "examples", "twins"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(repo, d),
                        ignore=shutil.ignore_patterns("__pycache__"))
    py = sys.executable

    scan_cmd = "python3 scripts/twin_scan.py --corpus examples/sample-corpus --out patterns.json"
    scan_out, _ = run([py, "scripts/twin_scan.py", "--corpus", "examples/sample-corpus", "--out", "patterns.json"], repo)
    rep_cmd = "python3 scripts/twin_report.py patterns.json --out twin-report.html"
    rep_out, _ = run([py, "scripts/twin_report.py", "patterns.json", "--out", "twin-report.html"], repo)
    draft = "examples/drafts/supplier-update.md"
    fixed = "examples/drafts/supplier-update.fixed.md"
    rules = "twins/example/twin.rules.json"
    chk1_cmd = "python3 scripts/twin_check.py --rules %s %s" % (rules, draft)
    chk1_out, code1 = run([py, "scripts/twin_check.py", "--rules", rules, draft], repo)
    diff_cmd = "diff -u %s %s" % (draft, fixed)
    diff_out, _ = run(["diff", "-u", draft, fixed], repo)
    diff_out = "\n".join(l for l in diff_out.split("\n") if not l.startswith(("---", "+++")))
    chk2_cmd = "python3 scripts/twin_check.py --rules %s %s" % (rules, fixed)
    chk2_out, code2 = run([py, "scripts/twin_check.py", "--rules", rules, fixed], repo)
    if code1 != 1 or code2 != 0:
        raise SystemExit("unexpected exit codes %s %s; not building a demo of a broken run" % (code1, code2))
    report = os.path.join(repo, "twin-report.html")
    chk1_out += "exit code %d\n" % code1
    chk2_out += "exit code %d\n" % code2

    shots = []  # (path, seconds)
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception:
            browser = p.chromium.launch()

        def term(name, step, label, blocks, secs):
            page = browser.new_page(viewport={"width": W, "height": H})
            path = os.path.join(work, name + ".html")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(terminal_page(step, label, blocks, fonts))
            page.goto("file://" + path)
            page.wait_for_timeout(150)
            out = os.path.join(frames, name + ".png")
            page.screenshot(path=out)
            page.close()
            shots.append((out, secs))

        def report_shot(name, anchor, secs, page):
            page.evaluate("document.getElementById(%r).scrollIntoView({block:'start'})" % anchor)
            page.evaluate("window.scrollBy(0,-24)")
            page.wait_for_timeout(120)
            out = os.path.join(frames, name + ".png")
            page.screenshot(path=out)
            shots.append((out, secs))

        term("01-scan", "1/4", "scan a folder of writing", [(scan_cmd, scan_out)], 2.4)
        term("02-report", "2/4", "build the report", [(scan_cmd, scan_out), (rep_cmd, rep_out)], 1.4)

        page = browser.new_page(viewport={"width": W, "height": H}, color_scheme="dark")
        page.goto("file://" + report)
        if fonts:
            page.add_style_tag(content=font_css(fonts))
        page.wait_for_timeout(300)
        out = os.path.join(frames, "03-report-top.png")
        page.screenshot(path=out)
        shots.append((out, 2.2))
        report_shot("04-repeats", "sample-corpus-repeats", 1.8, page)
        report_shot("05-drift", "sample-corpus-drift", 2.2, page)
        report_shot("06-flags", "sample-corpus-flags", 2.0, page)

        hero = browser.new_page(viewport={"width": 1200, "height": 675}, color_scheme="dark")
        hero.goto("file://" + report)
        if fonts:
            hero.add_style_tag(content=font_css(fonts))
        # Scale to 90% so the score block and all six tiles fit in 675 px.
        hero.add_style_tag(content="html{zoom:.9}")
        hero.wait_for_timeout(300)
        hero.screenshot(path=args.out_hero)
        hero.close()
        page.close()

        term("07-check", "3/4", "check a draft against the twin's rules", [(chk1_cmd, chk1_out)], 2.6)
        term("08-fix", "4/4", "fix it", [(diff_cmd, diff_out)], 2.0)
        term("09-pass", "4/4", "check again", [(chk2_cmd, chk2_out)], 2.2)
        browser.close()

    total = sum(s for _, s in shots)
    if total >= 20:
        raise SystemExit("demo would run %.1f s; keep it under 20" % total)
    # Each screenshot becomes round(seconds x FPS) numbered frames, so the
    # GIF length is exact: frames / FPS.
    fps = 8
    seq = os.path.join(work, "seq")
    os.makedirs(seq)
    n = 0
    for path, secs in shots:
        for _ in range(int(round(secs * fps))):
            shutil.copyfile(path, os.path.join(seq, "%04d.png" % n))
            n += 1
    pattern = os.path.join(seq, "%04d.png")
    palette = os.path.join(work, "palette.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", pattern,
                    "-vf", "scale=%d:-1:flags=lanczos,palettegen=max_colors=64:stats_mode=full" % W,
                    palette], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", pattern, "-i", palette,
                    "-lavfi", "scale=%d:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=none" % W,
                    "-loop", "0", args.out_gif], check=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            args.out_gif], capture_output=True, text=True, check=True)
    seconds = float(probe.stdout.strip())
    if seconds >= 20:
        raise SystemExit("the GIF runs %.2f s; keep it under 20" % seconds)
    print("wrote %s (%.2f s measured, %d KB)" % (args.out_gif, seconds, os.path.getsize(args.out_gif) // 1024))
    print("wrote %s" % args.out_hero)
    if args.keep:
        print("frames kept in %s" % frames)
    else:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()

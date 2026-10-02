#!/usr/bin/env python3
"""Build the README visuals from real runs on the synthetic sample.

Dev-only. Not needed to use the twin scripts. Needs:
  - Python with Playwright (pip install playwright) and Google Chrome or a
    Playwright Chromium
  - ffmpeg and ffprobe on PATH
  - optional: --font-dir holding Archivo-VF.ttf and IBMPlexMono-Regular.ttf
    (both SIL OFL). They are injected into the captured pages only; the
    shipped report never loads fonts.

What it does:
  1. Copies scripts/, examples/ and twins/ into a temp folder and runs
     twin_scan.py, twin_report.py and twin_check.py there.
  2. Feeds their real output into the film (tools/demo/film.py) and renders
     it frame by frame, so every number and sentence on screen comes from
     those runs. Stitches the frames into assets/film.gif.
  3. Draws the report still (assets/report.png) and the diagram from the same
     data, captures the real report for assets/hero.png, and builds the
     share card.

  python tools/demo/make_demo.py --font-dir /path/to/fonts
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import diagram  # noqa: E402
import film  # noqa: E402
import social  # noqa: E402
import still  # noqa: E402

FPS = 20
GIF_WIDTH = 1280


def font_css(font_dir):
    if not font_dir:
        return ""
    return ('@font-face{font-family:"Archivo";src:url("file://%s/Archivo-VF.ttf");font-weight:100 900;'
            'font-stretch:62%% 125%%}@font-face{font-family:"IBM Plex Mono";'
            'src:url("file://%s/IBMPlexMono-Regular.ttf")}' % (font_dir, font_dir))


def run(cmd, cwd):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.stdout, proc.returncode


def line_of(path, n):
    with open(path, encoding="utf-8") as fh:
        return fh.read().split("\n")[n - 1]


def encode_gif(frames_dir, out, work):
    pattern = os.path.join(frames_dir, "%04d.png")
    palette = os.path.join(work, "palette.png")
    scale = "scale=%d:-1:flags=lanczos" % GIF_WIDTH
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", pattern,
                    "-vf", scale + ",palettegen=max_colors=64:stats_mode=diff", palette], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", pattern, "-i", palette,
                    "-lavfi", scale + "[x];[x][1:v]paletteuse=dither=none:diff_mode=rectangle",
                    "-loop", "0", out], check=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                           capture_output=True, text=True, check=True)
    return float(probe.stdout.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--font-dir")
    ap.add_argument("--out-film", default=os.path.join(ROOT, "assets", "film.gif"))
    ap.add_argument("--out-hero", default=os.path.join(ROOT, "assets", "hero.png"))
    ap.add_argument("--out-still", default=os.path.join(ROOT, "assets", "report.png"))
    ap.add_argument("--out-diagram", default=os.path.join(ROOT, "assets", "how-it-works.png"))
    ap.add_argument("--out-social", default=os.path.join(ROOT, "assets", "social-preview.png"))
    ap.add_argument("--stills", help="also save a full-size still every half second into this folder")
    ap.add_argument("--keep", action="store_true", help="keep the temp folder")
    args = ap.parse_args()
    fonts = os.path.abspath(args.font_dir) if args.font_dir else None
    css = font_css(fonts)

    from playwright.sync_api import sync_playwright

    work = tempfile.mkdtemp(prefix="twin-demo-")
    repo = os.path.join(work, "repo")
    for d in ("scripts", "examples", "twins"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(repo, d), ignore=shutil.ignore_patterns("__pycache__"))
    py = sys.executable
    run([py, "scripts/twin_scan.py", "--corpus", "examples/sample-corpus", "--out", "patterns.json"], repo)
    run([py, "scripts/twin_report.py", "patterns.json", "--out", "twin-report.html"], repo)
    draft = "examples/drafts/supplier-update.md"
    fixed = "examples/drafts/supplier-update.fixed.md"
    rules = "twins/example/twin.rules.json"
    out1, code1 = run([py, "scripts/twin_check.py", "--rules", rules, draft, "--format", "json"], repo)
    _, code2 = run([py, "scripts/twin_check.py", "--rules", rules, fixed], repo)
    if code1 != 1 or code2 != 0:
        raise SystemExit("unexpected exit codes %s %s; not building visuals of a broken run" % (code1, code2))
    with open(os.path.join(repo, "patterns.json"), encoding="utf-8") as fh:
        patterns = json.load(fh)
    check = json.loads(out1)
    hit_line = check["results"][0]["hits"][0]["line"]
    data = film.build_data(patterns, check, line_of(os.path.join(repo, draft), hit_line),
                           line_of(os.path.join(repo, fixed), hit_line))
    report = os.path.join(repo, "twin-report.html")

    frames = os.path.join(work, "frames")
    os.makedirs(frames)
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception:
            browser = p.chromium.launch()

        # The film, frame by frame.
        fpath = os.path.join(work, "film.html")
        with open(fpath, "w", encoding="utf-8") as fh:
            fh.write(film.build_page(data, css))
        page = browser.new_page(viewport={"width": film.W, "height": film.H})
        page.goto("file://" + fpath)
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(300)
        n = int(round(film.DURATION * FPS))
        for i in range(n):
            page.evaluate("(t) => window.render(t)", film.START + i / FPS)
            page.screenshot(path=os.path.join(frames, "%04d.png" % i))
        if args.stills:
            os.makedirs(args.stills, exist_ok=True)
            for i in range(0, n, FPS // 2):
                shutil.copyfile(os.path.join(frames, "%04d.png" % i),
                                os.path.join(args.stills, "t%05.2f.png" % (film.START + i / FPS)))
        page.close()

        # The real report, finished state.
        hero = browser.new_page(viewport={"width": 1200, "height": 675}, color_scheme="dark",
                                reduced_motion="reduce")
        hero.goto("file://" + report)
        if css:
            hero.add_style_tag(content=css)
        hero.add_style_tag(content="html{zoom:.9}")
        hero.wait_for_timeout(300)
        hero.screenshot(path=args.out_hero)
        hero.close()

        dpath = os.path.join(work, "diagram.html")
        with open(dpath, "w", encoding="utf-8") as fh:
            fh.write(diagram.page(css))
        dpage = browser.new_page(viewport={"width": diagram.W, "height": diagram.H}, device_scale_factor=2)
        dpage.goto("file://" + dpath)
        dpage.wait_for_timeout(300)
        dpage.screenshot(path=args.out_diagram)
        dpage.close()

        rpath = os.path.join(work, "still.html")
        with open(rpath, "w", encoding="utf-8") as fh:
            fh.write(still.page(patterns, css))
        rpage = browser.new_page(viewport={"width": still.W, "height": still.H}, device_scale_factor=2)
        rpage.goto("file://" + rpath)
        rpage.wait_for_timeout(300)
        rpage.screenshot(path=args.out_still)
        rpage.close()

        spath = os.path.join(work, "social.html")
        with open(spath, "w", encoding="utf-8") as fh:
            fh.write(social.page(os.path.abspath(args.out_hero), css))
        spage = browser.new_page(viewport={"width": social.W, "height": social.H}, device_scale_factor=2)
        spage.goto("file://" + spath)
        spage.wait_for_timeout(300)
        spage.screenshot(path=args.out_social)
        spage.close()
        browser.close()

    seconds = encode_gif(frames, args.out_film, work)
    if seconds >= 20:
        raise SystemExit("the film runs %.2f s; keep it under 20" % seconds)
    print("wrote %s (%.2f s, %d KB)" % (args.out_film, seconds, os.path.getsize(args.out_film) // 1024))
    for path in (args.out_still, args.out_hero, args.out_diagram, args.out_social):
        print("wrote %s" % path)
    if args.keep:
        print("kept %s" % work)
    else:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()

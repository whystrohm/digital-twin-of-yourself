#!/usr/bin/env python3
"""The share card for GitHub's social preview (1280 x 640), built from the real hero image.

make_demo.py renders it to assets/social-preview.png. Palette only.
"""

import html

W, H = 1280, 640


def page(hero_path, font_css=""):
    return """<!doctype html><html><head><meta charset="utf-8"><style>%s
html,body{margin:0;background:#07080A}
body{width:%dpx;height:%dpx;overflow:hidden;position:relative;color:#F6F5F2;font-family:"Archivo",Arial,sans-serif}
.l{position:absolute;left:64px;top:64px;width:520px}
.eb{font:500 15px "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.16em;color:#E4552A;text-transform:uppercase}
h1{font-size:76px;line-height:.92;font-weight:800;font-stretch:80%%;letter-spacing:-.02em;margin:22px 0 26px}
p{font-size:25px;line-height:1.35;color:rgba(246,245,242,.66);margin:0;max-width:470px}
.f{position:absolute;left:64px;bottom:56px;font:500 15px "IBM Plex Mono",ui-monospace,monospace;color:rgba(246,245,242,.66);letter-spacing:.04em}
.f b{color:#F6F5F2;font-weight:500}
.r{position:absolute;left:640px;top:64px;width:720px;height:540px;overflow:hidden;
border:1px solid rgba(246,245,242,.22);border-right:0;border-radius:4px 0 0 4px}
.r img{width:900px;display:block;margin:-40px 0 0 -70px}
</style></head><body>
<div class="l"><div class="eb">Open source &middot; runs offline</div>
<h1>Digital Twin of Yourself</h1>
<p>See how you actually write. Then check every draft, yours or an AI&#8217;s, against it.</p></div>
<div class="f"><b>github.com/whystrohm</b> &nbsp;/&nbsp; digital-twin-of-yourself</div>
<div class="r"><img src="file://%s" alt=""></div>
</body></html>""" % (font_css, W, H, html.escape(hero_path))

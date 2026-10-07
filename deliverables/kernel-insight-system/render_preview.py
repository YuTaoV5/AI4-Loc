#!/usr/bin/env python3
"""逐页渲染 deck，再拼成一张 contact sheet 用于自查。

用法:  python3 render_preview.py deck.html <页数> <输出目录> [缩放=1]
产物:  <输出目录>/slide-01.png ... 和 <输出目录>/contact.png
依赖:  pillow + 本机装了 Chrome（或用 CHROME 环境变量指路径）
"""
import os, subprocess, sys, pathlib, uuid, shutil
from PIL import Image

CANDIDATES = [
    os.environ.get("CHROME", ""),
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
]
CHROME = next((c for c in CANDIDATES if c and pathlib.Path(c).exists()), None)
if not CHROME:
    sys.exit("找不到 Chrome，用 CHROME=/path/to/chrome 指定")

deck = pathlib.Path(sys.argv[1]).resolve()
n = int(sys.argv[2])
out = pathlib.Path(sys.argv[3]).resolve(); out.mkdir(parents=True, exist_ok=True)
scale = sys.argv[4] if len(sys.argv) > 4 else "1"
profile = out / ('chrome-profile-' + uuid.uuid4().hex)
profile.mkdir()
pages = [int(x) for x in os.environ.get('KELIP_RENDER_PAGES', '').split(',') if x] or range(1, n + 1)

for i in pages:
    png = out / f"slide-{i:02d}.png"
    temporary_png = out / f"pending-{i:02d}-{uuid.uuid4().hex}.png"
    result = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--virtual-time-budget=4000", f"--user-data-dir={profile}", f"--force-device-scale-factor={scale}",
                    f"--screenshot={temporary_png}", "--window-size=1920,1080",
                    deck.as_uri() + f"#{i}"], capture_output=True, timeout=45)
    if result.returncode or not temporary_png.exists():
        sys.exit(f"Rendering failed on slide {i}: {result.stderr[-1500:]!r}")
    with Image.open(temporary_png) as verification_image:
        verification_image.verify()
    temporary_png.replace(png)
    print(png.name, png.exists() and png.stat().st_size, flush=True)

if profile.resolve().parent == out.resolve() and profile.name.startswith('chrome-profile-'):
    shutil.rmtree(profile, ignore_errors=True)

# contact sheet: 4 列，每格 480×270
tiles = [Image.open(out / f"slide-{i:02d}.png") for i in range(1, n + 1)]
tw, th, cols, gap = 480, 270, 4, 10
rows = (n + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap), (200, 205, 212))
for k, t in enumerate(tiles):
    r, c = divmod(k, cols)
    sheet.paste(t.resize((tw, th), Image.LANCZOS), (gap + c * (tw + gap), gap + r * (th + gap)))
sheet.save(out / "contact.png"); sheet.save(deck.parent / "预览-全部页面.png"); print("contact", sheet.size)

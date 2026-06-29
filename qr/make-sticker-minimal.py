#!/usr/bin/env python3
"""Minimal ORDER NOW window sticker, white-on-transparent (per founder request
2026-06-29): same as the liked sticker-4-dark-white design but with the top
wordmark and the "Scan to order" caption REMOVED. Keeps ORDER NOW + the QR with
its centre runner-arch icon. Renders a dark-background PREVIEW too (the raw art
is white-on-clear, so it is invisible on a white viewer) and verifies the code
still decodes. Re-run: cd theacaiclub/web && python3 qr/make-sticker-minimal.py
"""
import os, importlib.util
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "qr_codes", "white-transparent")
os.makedirs(OUT, exist_ok=True)

spec = importlib.util.spec_from_file_location("mq", os.path.join(HERE, "make-qr.py"))
mq = importlib.util.module_from_spec(spec); spec.loader.exec_module(mq)

QR = "https://theacaiclub.com/qr"
STORES = ["datchet"]   # add "beaconsfield", "reading" to roll out the set

for slug in STORES:
    url = f"{QR}/{slug}"
    out = os.path.join(OUT, f"sticker-ordernow-{slug}-white.png")
    mq.make_sticker(url, out, headline=["ORDER NOW"], instruction=None,
                    wordmark=False, dark=True, transparent=True)
    # composite the transparent art onto near-black so it is viewable / printable-on-dark
    art = Image.open(out).convert("RGBA")
    prev_img = Image.alpha_composite(Image.new("RGBA", art.size, (26, 26, 26, 255)), art).convert("RGB")
    prev = os.path.join(OUT, f"sticker-ordernow-{slug}-white-PREVIEW-on-dark.png")
    prev_img.save(prev)
    print(f"{os.path.basename(out):40s} decode(on-dark)={mq.verify(prev, url)}")
    print(f"{os.path.basename(prev):40s} preview")

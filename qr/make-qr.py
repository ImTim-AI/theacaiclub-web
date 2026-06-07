#!/usr/bin/env python3
"""Make a circular-style Acai Club QR (the variant T liked): brand colours, the
'THE ACAI CLUB' wordmark lockup on a round centre plate, decode-verified.

Usage:
    python3 qr/make-qr.py "<url>" "<output_name>"
e.g. python3 qr/make-qr.py "https://instagram.com/..." "runclub-instagram"
Writes qr/<output_name>.png
"""
import sys, os
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageChops, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
BG = (245, 241, 236)   # #f5f1ec
FG = "#1a1a1a"
SPLASH = os.path.join(HERE, "..", "..", "app", "assets", "images", "splash-screen.png")

def lockup_rgba():
    src = Image.open(SPLASH).convert("RGB")
    bgc = src.getpixel((5, 5))
    diff = ImageChops.difference(src, Image.new("RGB", src.size, bgc)).convert("L")
    x0, y0, x1, y1 = diff.point(lambda p: 255 if p > 9 else 0).getbbox()
    pad = 10
    crop = src.crop((x0 - pad, y0 - pad, x1 + pad, y1 + pad))
    alpha = ImageChops.difference(crop, Image.new("RGB", crop.size, bgc)).convert("L")
    alpha = alpha.point(lambda p: min(255, int(p / 32 * 255)))
    out = crop.convert("RGBA"); out.putalpha(alpha)
    return out

def make_circle(url, out_path):
    lk0 = lockup_rgba(); lw, lh = lk0.size
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=24, border=4)
    qr.add_data(url); qr.make(fit=True)
    img = qr.make_image(fill_color=FG, back_color="#f5f1ec").convert("RGBA")
    W, H = img.size

    # logo sized to sit inside a circular plate
    lk = lk0.resize((int(W * 0.26), int(lh * (W * 0.26 / lw))), Image.LANCZOS)
    lkw, lkh = lk.size
    side = int((lkw**2 + lkh**2) ** 0.5) + int(lkw * 0.10)   # diagonal + margin
    plate = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, side - 1, side - 1], fill=255)
    plate.paste(Image.new("RGBA", (side, side), BG + (255,)), (0, 0), mask)

    px, py = (W - side) // 2, (H - side) // 2
    img.alpha_composite(plate, (px, py))
    img.alpha_composite(lk, (px + (side - lkw) // 2, py + (side - lkh) // 2))
    img.convert("RGB").save(out_path)
    return out_path

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    url, name = sys.argv[1], sys.argv[2]
    out = os.path.join(HERE, name + ".png")
    make_circle(url, out)
    try:
        import cv2
        data, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imread(out))
        ok = ("OK -> " + data) if data == url else f"WARNING decode mismatch: {data!r}"
    except Exception as e:
        ok = f"(decode check skipped: {e})"
    print("wrote", out, "|", ok)

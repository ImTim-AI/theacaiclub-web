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
from PIL import Image, ImageChops, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BG = (245, 241, 236)   # #f5f1ec
FG = "#1a1a1a"
LOGO_DARK = (58, 58, 56)   # #3A3A38 — the wordmark/logo dark tone (app primaryColor)
FUT = "/System/Library/Fonts/Supplemental/Futura.ttc"   # 0 = Medium
SPLASH = os.path.join(HERE, "..", "..", "app", "assets", "images", "splash-screen.png")

def instagram_glyph(size, color):
    """Draw a simple Instagram camera glyph (rounded square + lens + dot)."""
    s = size * 4   # supersample for smooth edges
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    stroke = max(2, int(s * 0.085))
    inset = stroke // 2 + int(s * 0.02)
    d.rounded_rectangle([inset, inset, s - inset, s - inset],
                        radius=int(s * 0.30), outline=color, width=stroke)
    r = int(s * 0.21)
    c = s // 2
    d.ellipse([c - r, c - r, c + r, c + r], outline=color, width=stroke)
    dot = int(s * 0.055)
    dc = (int(s * 0.74), int(s * 0.26))
    d.ellipse([dc[0] - dot, dc[1] - dot, dc[0] + dot, dc[1] + dot], fill=color)
    return img.resize((size, size), Image.LANCZOS)

def label_row(text, color, max_w):
    """An [IG icon] + text row as one transparent image, scaled to <= max_w wide."""
    fsize = 64
    f = ImageFont.truetype(FUT, fsize, index=0)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tb = tmp.textbbox((0, 0), text, font=f)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    icon = th + int(th * 0.25)
    gap = int(th * 0.4)
    row_w, row_h = icon + gap + tw, max(icon, th)
    img = Image.new("RGBA", (row_w, row_h), (0, 0, 0, 0))
    img.alpha_composite(instagram_glyph(icon, color), (0, (row_h - icon) // 2))
    ImageDraw.Draw(img).text((icon + gap, (row_h - th) // 2 - tb[1]), text, font=f, fill=color)
    if row_w > max_w:    # scale down to fit one line in the circle
        scale = max_w / row_w
        img = img.resize((int(row_w * scale), int(row_h * scale)), Image.LANCZOS)
    return img

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

def logo_ink(crop_rgba):
    """Exact logo ink colour = average of the darkest (most-inked) pixels."""
    rgb = crop_rgba.convert("RGB")
    px = list(rgb.get_flattened_data() if hasattr(rgb, "get_flattened_data") else rgb.getdata())
    darks = sorted(px, key=lambda c: sum(c))[:max(50, len(px) // 50)]
    n = len(darks)
    return (sum(c[0] for c in darks)//n, sum(c[1] for c in darks)//n, sum(c[2] for c in darks)//n)

def make_circle(url, out_path, label=None):
    lk0 = lockup_rgba(); lw, lh = lk0.size
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=24, border=4)
    qr.add_data(url); qr.make(fit=True)
    img = qr.make_image(fill_color=FG, back_color="#f5f1ec").convert("RGBA")
    W, H = img.size

    # logo + circle geometry — IDENTICAL to the original (unaffected by the label)
    lk = lk0.resize((int(W * 0.26), int(lh * (W * 0.26 / lw))), Image.LANCZOS)
    lkw, lkh = lk.size
    side = int((lkw**2 + lkh**2) ** 0.5) + int(lkw * 0.10)   # diagonal + margin
    plate = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, side - 1, side - 1], fill=255)
    plate.paste(Image.new("RGBA", (side, side), BG + (255,)), (0, 0), mask)

    px, py = (W - side) // 2, (H - side) // 2
    img.alpha_composite(plate, (px, py))
    lx, ly = px + (side - lkw) // 2, py + (side - lkh) // 2   # logo centred (original)
    img.alpha_composite(lk, (lx, ly))

    # small IG + label line, tucked into the empty space below the centred logo
    if label:
        row = label_row(label, logo_ink(lk0), max_w=int(lkw * 0.55))
        target_h = int(lkh * 0.165)                           # slightly smaller
        if row.size[1] != target_h:
            row = row.resize((int(row.size[0] * target_h / row.size[1]), target_h), Image.LANCZOS)
        ry = ly + lkh + int(lkh * 0.12)                       # just below the logo (higher up)
        img.alpha_composite(row, (px + (side - row.size[0]) // 2, ry))

    img.convert("RGB").save(out_path)
    return out_path

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    url, name = sys.argv[1], sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else None
    out = os.path.join(HERE, name + ".png")
    make_circle(url, out, label=label)
    try:
        import cv2
        data, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imread(out))
        ok = ("OK -> " + data) if data == url else f"WARNING decode mismatch: {data!r}"
    except Exception as e:
        ok = f"(decode check skipped: {e})"
    print("wrote", out, "|", ok)

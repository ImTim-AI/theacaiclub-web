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

def mobile_glyph(size, color):
    """Draw a simple phone outline (rounded body + speaker + home indicator)."""
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    stroke = max(2, int(s * 0.075))
    bw = int(s * 0.56)                      # phone is taller than wide
    x0, x1 = (s - bw) // 2, (s + bw) // 2
    d.rounded_rectangle([x0, int(s * 0.06), x1, int(s * 0.94)],
                        radius=int(s * 0.14), outline=color, width=stroke)
    d.line([s // 2 - int(s * 0.07), int(s * 0.135), s // 2 + int(s * 0.07), int(s * 0.135)],
           fill=color, width=max(2, int(s * 0.045)))                       # speaker
    d.line([s // 2 - int(s * 0.09), int(s * 0.875), s // 2 + int(s * 0.09), int(s * 0.875)],
           fill=color, width=max(2, int(s * 0.05)))                        # home indicator
    return img.resize((size, size), Image.LANCZOS)

def label_block(lines, color, icon_fn=instagram_glyph):
    """[icon] + text laid out over one or more lines, as one transparent image.
    The icon (if any) sits inline before the first line; every line is centred.
    Pass icon_fn=None for a text-only label."""
    fsize = 64
    f = ImageFont.truetype(FUT, fsize, index=0)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    def tsize(t):
        b = tmp.textbbox((0, 0), t, font=f); return b[2]-b[0], b[3]-b[1], b
    th = tsize("RUN CLUB")[1]
    icon = (th + int(th * 0.22)) if icon_fn else 0
    gap = int(th * 0.42) if icon_fn else 0    # icon -> text gap
    lgap = int(th * 0.45)                       # line spacing

    widths = []
    for i, ln in enumerate(lines):
        w = tsize(ln)[0] + (icon + gap if i == 0 else 0)
        widths.append(w)
    block_w = max(widths)
    line_h = max(icon, th)
    block_h = line_h * len(lines) + lgap * (len(lines) - 1)

    img = Image.new("RGBA", (block_w, block_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 0
    for i, ln in enumerate(lines):
        tw, _, b = tsize(ln)
        row_w = tw + (icon + gap if i == 0 else 0)
        x = (block_w - row_w) // 2
        if i == 0 and icon_fn:
            img.alpha_composite(icon_fn(icon, color), (x, y + (line_h - icon) // 2))
            x += icon + gap
        d.text((x, y + (line_h - th) // 2 - b[1]), ln, font=f, fill=color)
        y += line_h + lgap
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

def make_circle(url, out_path, lines=None, icon="instagram"):
    import math
    lk0 = lockup_rgba(); lw, lh = lk0.size
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=24, border=4)
    qr.add_data(url); qr.make(fit=True)
    img = qr.make_image(fill_color=FG, back_color="#f5f1ec").convert("RGBA")
    W, H = img.size

    # logo at its fixed size (never changes)
    lk = lk0.resize((int(W * 0.26), int(lh * (W * 0.26 / lw))), Image.LANCZOS)
    lkw, lkh = lk.size
    ink = logo_ink(lk0)

    # build the label block (if any), scaled so it never exceeds the logo width
    block = None
    if lines:
        icon_fn = {"mobile": mobile_glyph, "none": None}.get(icon, instagram_glyph)
        block = label_block(lines, ink, icon_fn)
        max_w = int(lkw * 0.92)
        # extra shrink for multi-line so the centre plate stays small enough to scan
        max_w = int(max_w * (0.78 if len(lines) > 1 else 1.0))
        if block.size[0] > max_w:
            sc = max_w / block.size[0]
            block = block.resize((int(block.size[0] * sc), int(block.size[1] * sc)), Image.LANCZOS)
        bw, bh = block.size
        gap = int(lkh * 0.12)

    # logo + label centred as a group -> compact circle that still scans
    content_w = max(lkw, bw if block else 0)
    content_h = lkh + (gap + bh if block else 0)
    margin = int(lkw * 0.09)
    r = math.hypot(content_w, content_h) / 2 + margin
    side = int(2 * r)

    plate = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, side - 1, side - 1], fill=255)
    plate.paste(Image.new("RGBA", (side, side), BG + (255,)), (0, 0), mask)

    px, py = (W - side) // 2, (H - side) // 2
    cx, cy = px + side // 2, py + side // 2
    img.alpha_composite(plate, (px, py))
    top = cy - content_h // 2
    img.alpha_composite(lk, (cx - lkw // 2, top))
    if block:
        img.alpha_composite(block, (cx - bw // 2, top + lkh + gap))

    img.convert("RGB").save(out_path)
    return out_path

def verify(out, url):
    try:
        import cv2
        data, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imread(out))
        return ("OK -> " + data) if data == url else f"WARNING decode mismatch: {data!r}"
    except Exception as e:
        return f"(decode check skipped: {e})"

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__ + "\nLabel: use '|' to split lines, '--mobile' for the phone icon.")
        sys.exit(1)
    url, name = sys.argv[1], sys.argv[2]
    icon = "mobile" if "--mobile" in sys.argv else ("none" if "--no-icon" in sys.argv else "instagram")
    label = next((a for a in sys.argv[3:] if not a.startswith("--")), None)
    lines = label.split("|") if label else None
    out = os.path.join(HERE, name + ".png")
    make_circle(url, out, lines=lines, icon=icon)
    print("wrote", out, "|", verify(out, url))

#!/usr/bin/env python3
"""Generate The Acai Club app QR codes with the wordmark lockup in the centre.
Produces three plate shapes so the client can pick: rounded, circle, rectangle.
Re-run any time: `python3 qr/generate-qr.py` from web/.
"""
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageChops, ImageDraw

URL = "https://theacaiclub.com/get"
BG = (245, 241, 236)        # #f5f1ec  (QR background / plate colour)
FG = "#1a1a1a"
SPLASH = "../app/assets/images/splash-screen.png"

def lockup_rgba():
    """Crop the wordmark lockup from the app splash and knock its beige bg out."""
    src = Image.open(SPLASH).convert("RGB")
    bgc = src.getpixel((5, 5))
    diff = ImageChops.difference(src, Image.new("RGB", src.size, bgc)).convert("L")
    x0, y0, x1, y1 = diff.point(lambda p: 255 if p > 9 else 0).getbbox()
    pad = 10
    crop = src.crop((x0 - pad, y0 - pad, x1 + pad, y1 + pad))
    alpha = ImageChops.difference(crop, Image.new("RGB", crop.size, bgc)).convert("L")
    alpha = alpha.point(lambda p: min(255, int(p / 32 * 255)))
    out = crop.convert("RGBA")
    out.putalpha(alpha)
    return out

def build(shape, out_path):
    lk0 = lockup_rgba()
    lw, lh = lk0.size

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=24, border=4)
    qr.add_data(URL); qr.make(fit=True)
    img = qr.make_image(fill_color=FG, back_color="#f5f1ec").convert("RGBA")
    W, H = img.size

    if shape == "circle":
        # square plate + circular mask; logo sized to sit inside the circle
        lk = lk0.resize((int(W * 0.26), int(lh * (W * 0.26 / lw))), Image.LANCZOS)
        lkw, lkh = lk.size
        side = int((lkw**2 + lkh**2) ** 0.5) + int(lkw * 0.10)  # diag + margin
        pw = ph = side
        radius = side // 2
    else:
        lk = lk0.resize((int(W * 0.30), int(lh * (W * 0.30 / lw))), Image.LANCZOS)
        lkw, lkh = lk.size
        padx, pady = int(lkw * 0.12), int(lkh * 0.26)
        pw, ph = lkw + 2 * padx, lkh + 2 * pady
        radius = 0 if shape == "rectangle" else int(ph * 0.30)

    plate = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    mask = Image.new("L", (pw, ph), 0)
    d = ImageDraw.Draw(mask)
    if shape == "circle":
        d.ellipse([0, 0, pw - 1, ph - 1], fill=255)
    else:
        d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=radius, fill=255)
    plate.paste(Image.new("RGBA", (pw, ph), BG + (255,)), (0, 0), mask)

    px, py = (W - pw) // 2, (H - ph) // 2
    img.alpha_composite(plate, (px, py))
    img.alpha_composite(lk, (px + (pw - lk.size[0]) // 2, py + (ph - lk.size[1]) // 2))
    img.convert("RGB").save(out_path)
    return out_path, (pw, ph), (W, H)

if __name__ == "__main__":
    import cv2
    for shape, name in [("rounded", "theacaiclub-app-qr.png"),
                        ("circle",  "theacaiclub-app-qr-circle.png"),
                        ("rectangle", "theacaiclub-app-qr-rectangle.png")]:
        path, plate, full = build(shape, "qr/" + name)
        data, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imread(path))
        ok = "OK -> " + data if data else "DECODE FAILED"
        print(f"{shape:10s} plate {100*plate[0]/full[0]:.0f}%x{100*plate[1]/full[1]:.0f}%  {ok}  ({name})")

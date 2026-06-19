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
BG = (245, 241, 236)   # #f5f1ec  light background / module-on-light
FG = "#1a1a1a"         # dark modules
DARK_BG = (26, 26, 26)     # #1a1a1a  near-black (for black-acrylic / dark prints)
LIGHT = (245, 241, 236)    # #f5f1ec  brand cream — the "white" on dark versions
LOGO_DARK = (58, 58, 56)   # #3A3A38 — the wordmark/logo dark tone (app primaryColor)
FUT = "/System/Library/Fonts/Supplemental/Futura.ttc"   # 0 = Medium
# Montserrat = the brand's declared Gotham fallback (Gotham is licensed/not installed).
# Bundled OFL font so renders are reproducible on any machine.
MONT = os.path.join(HERE, "fonts", "Montserrat.ttf")
SPLASH = os.path.join(HERE, "..", "..", "app", "assets", "images", "splash-screen.png")
# The runner-arch app icon alone (no wordmark), 1024px — high-res source for a QR
# centre mark when the full wordmark already appears elsewhere (e.g. sticker top).
ICON = os.path.join(HERE, "..", "..", "app", "ios", "Runner", "Assets.xcassets",
                    "AppIcon.appiconset", "Icon-App-1024x1024@1x.png")

def load_font(path, size, index=0, weight=None):
    f = ImageFont.truetype(path, size, index=index)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f

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

def label_block(lines, color, icon_fn=instagram_glyph, font=None):
    """[icon] + text laid out over one or more lines, as one transparent image.
    The icon (if any) sits inline before the first line; every line is centred.
    Pass icon_fn=None for a text-only label. `font` overrides the default Futura."""
    fsize = 64
    f = font if font is not None else ImageFont.truetype(FUT, fsize, index=0)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    _, descent = f.getmetrics()                 # max descender depth below baseline (g, p, y)
    cap_h = tmp.textbbox((0, 0), "RUN CLUB", font=f)[3]   # caps height
    def tw(t):
        return tmp.textlength(t, font=f)
    icon = (cap_h + int(cap_h * 0.22)) if icon_fn else 0
    gap = int(cap_h * 0.42) if icon_fn else 0   # icon -> text gap
    lgap = int(cap_h * 0.45)                     # spacing between lines (matches the liked layout)

    row_h = max(icon, cap_h)
    block_w = int(max(tw(ln) + (icon + gap if i == 0 else 0) for i, ln in enumerate(lines)))
    # +descent of bottom padding so the final line's descenders (g, p, y) aren't clipped
    block_h = row_h * len(lines) + lgap * (len(lines) - 1) + descent

    img = Image.new("RGBA", (block_w, block_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 0
    for i, ln in enumerate(lines):
        row_w = int(tw(ln)) + (icon + gap if i == 0 else 0)
        x = (block_w - row_w) // 2
        if i == 0 and icon_fn:
            img.alpha_composite(icon_fn(icon, color), (x, y + (row_h - icon) // 2))
            x += icon + gap
        baseline = y + (row_h - cap_h) // 2 + cap_h        # caps fill the row
        d.text((x, baseline), ln, font=f, fill=color, anchor="ls")
        y += row_h + lgap
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

def icon_mark_rgba():
    """Just the runner-arch app-icon mark (no wordmark text), knocked out of the
    1024px app icon. Crisp, high-res; for use as a QR centre when the full wordmark
    is shown elsewhere (avoids the logo appearing twice)."""
    src = Image.open(ICON).convert("RGB")
    bgc = src.getpixel((5, 5))
    diff = ImageChops.difference(src, Image.new("RGB", src.size, bgc)).convert("L")
    x0, y0, x1, y1 = diff.point(lambda p: 255 if p > 18 else 0).getbbox()
    pad = 8
    crop = src.crop((max(0, x0 - pad), max(0, y0 - pad),
                     min(src.size[0], x1 + pad), min(src.size[1], y1 + pad)))
    alpha = ImageChops.difference(crop, Image.new("RGB", crop.size, bgc)).convert("L")
    alpha = alpha.point(lambda p: 0 if p < 24 else (255 if p > 70 else int((p - 24) / 46 * 255)))
    out = crop.convert("RGBA"); out.putalpha(alpha)
    return out

def logo_ink(crop_rgba):
    """Exact logo ink colour = average of the darkest (most-inked) pixels."""
    rgb = crop_rgba.convert("RGB")
    px = list(rgb.get_flattened_data() if hasattr(rgb, "get_flattened_data") else rgb.getdata())
    darks = sorted(px, key=lambda c: sum(c))[:max(50, len(px) // 50)]
    n = len(darks)
    return (sum(c[0] for c in darks)//n, sum(c[1] for c in darks)//n, sum(c[2] for c in darks)//n)

def tint(rgba, color):
    """Recolour an RGBA glyph to `color`, preserving its alpha (used to make the
    dark-ink wordmark light for dark/black-acrylic versions)."""
    solid = Image.new("RGBA", rgba.size, color + (255,))
    solid.putalpha(rgba.getchannel("A"))
    return solid

def _compose(url, version, lines, icon, dark=False, centre_text=None, centre_scale=0.30, centre_img=None):
    """Render one circular QR at a specific version. Returns the RGB image.
    dark=True -> light modules/logo/text on a near-black background (black acrylic).
    centre_text=[...] -> put those text lines (e.g. ['ORDER NOW','Datchet']) on the
    centre plate INSTEAD of the wordmark logo (the 'Order Now centre' style)."""
    import math
    bg = DARK_BG if dark else BG            # canvas / plate colour
    fg = LIGHT if dark else FG              # qr module colour (a tuple or hex both work)
    fg_hex = "#%02x%02x%02x" % fg if isinstance(fg, tuple) else fg
    bg_hex = "#%02x%02x%02x" % bg
    ink = LIGHT if dark else None          # logo/text colour (None = sample from logo)

    lk0 = centre_img if centre_img is not None else lockup_rgba(); lw, lh = lk0.size
    qr = qrcode.QRCode(version=version, error_correction=ERROR_CORRECT_H, box_size=24, border=4)
    qr.add_data(url); qr.make(fit=(version is None))
    img = qr.make_image(fill_color=fg_hex, back_color=bg_hex).convert("RGBA")
    W, H = img.size

    # --- Centre-text style: text on the plate instead of the logo ---------------
    if centre_text:
        ink_c = LIGHT if dark else logo_ink(lk0)     # brand ink (sampled), even w/o the logo
        # brand font: Gotham -> Montserrat SemiBold fallback (same as stand captions)
        cfont = load_font(MONT, 64, weight=600) if os.path.exists(MONT) \
            else ImageFont.truetype(FUT, 64, index=0)
        tblk = label_block(centre_text, ink_c, icon_fn=None, font=cfont)
        target_w = int(W * centre_scale)             # legible but small enough to stay scannable
        sc = target_w / tblk.size[0]
        tblk = tblk.resize((max(1, int(tblk.size[0] * sc)), max(1, int(tblk.size[1] * sc))),
                           Image.LANCZOS)
        cw, ch = tblk.size
        margin = int(W * 0.055)
        side = int(2 * (math.hypot(cw, ch) / 2 + margin))
        plate = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        m = Image.new("L", (side, side), 0)
        ImageDraw.Draw(m).ellipse([0, 0, side - 1, side - 1], fill=255)
        plate.paste(Image.new("RGBA", (side, side), bg + (255,)), (0, 0), m)
        px, py = (W - side) // 2, (H - side) // 2
        img.alpha_composite(plate, (px, py))
        img.alpha_composite(tblk, (px + (side - cw) // 2, py + (side - ch) // 2))
        return img.convert("RGB")

    lk = lk0.resize((int(W * 0.26), int(lh * (W * 0.26 / lw))), Image.LANCZOS)
    lkw, lkh = lk.size
    if ink is None:
        ink = logo_ink(lk0)
    else:
        lk = tint(lk, ink)                 # recolour the wordmark light for dark mode

    block = bw = bh = gap = None
    if lines:
        icon_fn = {"mobile": mobile_glyph, "none": None}.get(icon, instagram_glyph)
        block = label_block(lines, ink, icon_fn)
        max_w = int(lkw * 0.92 * (0.78 if len(lines) > 1 else 1.0))
        if block.size[0] > max_w:
            sc = max_w / block.size[0]
            block = block.resize((int(block.size[0] * sc), int(block.size[1] * sc)), Image.LANCZOS)
        bw, bh = block.size
        gap = int(lkh * 0.12)

    content_w = max(lkw, bw or 0)
    content_h = lkh + ((gap + bh) if block else 0)
    margin = int(lkw * 0.09)
    side = int(2 * (math.hypot(content_w, content_h) / 2 + margin))

    plate = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, side - 1, side - 1], fill=255)
    plate.paste(Image.new("RGBA", (side, side), bg + (255,)), (0, 0), mask)

    px, py = (W - side) // 2, (H - side) // 2
    cx, cy = px + side // 2, py + side // 2
    img.alpha_composite(plate, (px, py))
    top = cy - content_h // 2
    img.alpha_composite(lk, (cx - lkw // 2, top))
    if block:
        img.alpha_composite(block, (cx - bw // 2, top + lkh + gap))
    return img.convert("RGB")

def _adaptive_qr(url, lines, icon, dark=False, centre_text=None, centre_scale=0.30, centre_img=None):
    """Return a circular-QR RGB image, auto-bumping the QR version until the
    finished image (centre plate and all) actually decodes."""
    import tempfile
    natural = _compose(url, None, lines, icon, dark, centre_text, centre_scale, centre_img)
    tmp = os.path.join(tempfile.gettempdir(), "_qrcheck.png")
    natural.save(tmp)
    if verify(tmp, url).startswith("OK"):
        return natural
    for v in range(2, 21):
        try:
            img = _compose(url, v, lines, icon, dark, centre_text, centre_scale, centre_img)
        except qrcode.exceptions.DataOverflowError:
            continue
        img.save(tmp)
        if verify(tmp, url).startswith("OK"):
            return img
    return natural   # fallback: nothing scanned cleanly, keep the natural one

def make_circle(url, out_path, lines=None, icon="instagram", dark=False):
    """Circular QR with the logo (and optional inline label) in the centre."""
    _adaptive_qr(url, lines, icon, dark).save(out_path)
    return out_path

def make_text_circle(url, out_path, text_lines, dark=False, centre_scale=0.30):
    """Circular QR with TEXT in the centre plate INSTEAD of the wordmark logo
    (the 'Order Now centre' style). `text_lines` = 1-2 short lines, e.g.
    ['ORDER NOW', 'Datchet']. `centre_scale` = how wide the text is vs the QR
    (0.30 default; bump to ~0.40 for a bigger 2-line centre). Auto-bumps version
    + decode-verifies like the others."""
    _adaptive_qr(url, None, "none", dark, centre_text=text_lines, centre_scale=centre_scale).save(out_path)
    return out_path

def make_stand(url, out_path, lines, icon="none", dark=False, caption_pos="below",
               centre_text=None, caption_full_width=False, caption_color=None):
    """Stand / menu poster: a circular QR with a caption in a band.
    caption_pos='below' (default) or 'above' the code. `lines` = caption text.
    centre_text=[...] -> text on the centre plate instead of the logo (e.g.
    ['FREE','REWARDS']); None = the wordmark logo. dark=True -> light on near-black.
    caption_full_width=True -> scale the caption to span (almost) the full QR width
    (big header look); the band grows to fit. caption_color overrides the ink
    (e.g. FG for black instead of the sampled logo grey)."""
    qr = _adaptive_qr(url, None, icon, dark, centre_text=centre_text)   # logo, or centre text
    W, _ = qr.size
    canvas_bg = DARK_BG if dark else BG
    ink = caption_color if caption_color is not None else (LIGHT if dark else logo_ink(lockup_rgba()))
    # Stand caption uses the brand font (Gotham → Montserrat fallback), SemiBold.
    mont = load_font(MONT, 64, weight=600) if os.path.exists(MONT) else None
    caption = label_block(lines, ink, icon_fn=None, font=mont)   # text-only, no icon

    if caption_full_width:
        # Big header: scale the caption to span the QR PATTERN width (the dark
        # modules), not the image width. The QR has a 4-module quiet-zone border at
        # box_size 24 -> 96px of cream each side, so the pattern is W-192 wide and
        # centred; matching that makes the header flush with the code, not overhanging.
        quiet = 4 * 24
        sc = (W - 2 * quiet) / caption.size[0]
        caption = caption.resize((int(caption.size[0] * sc), int(caption.size[1] * sc)), Image.LANCZOS)
        cw, ch = caption.size
        band_h = ch
        pad_top = int(W * 0.05)
        pad_bot = int(W * 0.05)
    else:
        # Scale to a fixed letter HEIGHT (not width) so every stand has the same text
        # size and the same total height regardless of wording — fronts/flipsides match.
        # Only shrink below that if the text would otherwise exceed the max width.
        target_h = int(W * 0.105)
        max_w = int(W * 0.86)
        sc = target_h / caption.size[1]
        if caption.size[0] * sc > max_w:
            sc = max_w / caption.size[0]
        caption = caption.resize((int(caption.size[0] * sc), int(caption.size[1] * sc)), Image.LANCZOS)
        cw, ch = caption.size
        band_h = int(W * 0.105)      # fixed caption band so canvas height is identical across stands
        pad_top = int(W * 0.04)      # gap between QR and caption band
        pad_bot = int(W * 0.07)      # breathing room under the caption
    total_h = W + pad_top + band_h + pad_bot
    canvas = Image.new("RGB", (W, total_h), canvas_bg)
    if caption_pos == "above":
        cy = pad_bot + (band_h - ch) // 2                 # caption in the top band
        canvas.paste(caption, ((W - cw) // 2, cy), caption)
        canvas.paste(qr, (0, pad_bot + band_h + pad_top))  # QR below the band
    else:
        canvas.paste(qr, (0, 0))
        cy = W + pad_top + (band_h - ch) // 2             # caption in the bottom band
        canvas.paste(caption, ((W - cw) // 2, cy), caption)
    canvas.save(out_path)
    return out_path

def make_sticker(url, out_path, headline=None, instruction="Scan to order",
                 dark=False, qr_centre_text=None, qr_frac=0.56, wordmark=True, S=1800):
    """Square (30x30cm-style) window-sticker poster, per the 2026-06-19 research:
    brand wordmark (anchor), a big headline CTA, the house-style QR on its cream
    panel (its own quiet zone), and a short instruction line.
    headline = list of 1-2 short lines (or None to omit). qr_centre_text puts text
    on the QR plate instead of the logo. dark=True -> near-black bg, cream art; the
    QR stays dark-on-light on its cream panel (never inverted)."""
    bg = DARK_BG if dark else BG
    art_ink = LIGHT if dark else logo_ink(lockup_rgba())   # wordmark + instruction tone
    head_ink = LIGHT if dark else FG                       # headline (true black on cream)
    canvas = Image.new("RGB", (S, S), bg)
    mont_bold = load_font(MONT, 64, weight=700) if os.path.exists(MONT) else None
    mont = load_font(MONT, 64, weight=600) if os.path.exists(MONT) else None

    els = []
    if wordmark:
        lk = lockup_rgba()
        # Sharpen the knockout alpha so the soft halo (visible once tinted on dark)
        # is removed, and never upscale past the source's native width so the
        # wordmark stays crisp. NOTE: the only logo asset is the ~467px splash crop;
        # a 30cm print needs the original high-res / vector lockup.
        a = lk.getchannel("A").point(lambda p: 0 if p < 40 else (255 if p > 95 else int((p - 40) / 55 * 255)))
        lk.putalpha(a)
        if dark:
            lk = tint(lk, LIGHT)
        ww = min(int(S * 0.42), lk.size[0]); wh = int(lk.size[1] * (ww / lk.size[0]))
        els.append(lk.resize((ww, wh), Image.LANCZOS))
    if headline:
        hblk = label_block(headline, head_ink, icon_fn=None, font=mont_bold)
        hsc = int(S * 0.82) / hblk.size[0]
        els.append(hblk.resize((max(1, int(hblk.size[0] * hsc)), max(1, int(hblk.size[1] * hsc))), Image.LANCZOS))
    # QR is always rendered light (dark-on-cream) so the cream forms its contrast panel.
    # Centre = the runner-arch ICON only (not the full wordmark) since the wordmark is
    # already the poster header; unless the centre is text (qr_centre_text).
    qr = _adaptive_qr(url, None, "none", False, centre_text=qr_centre_text,
                      centre_img=(None if qr_centre_text else icon_mark_rgba()))
    qside = int(S * qr_frac)
    els.append(qr.resize((qside, qside), Image.LANCZOS))
    if instruction:
        iblk = label_block([instruction], art_ink, icon_fn=None, font=mont)
        isc = int(S * 0.32) / iblk.size[0]
        els.append(iblk.resize((max(1, int(iblk.size[0] * isc)), max(1, int(iblk.size[1] * isc))), Image.LANCZOS))

    gap = int(S * 0.040)
    total = sum(e.size[1] for e in els) + gap * (len(els) - 1)
    # Fit guard: if the stack is taller than the safe area (e.g. a 2-line headline),
    # scale everything down so nothing overlaps the QR and breaks the scan.
    pad = int(S * 0.055)
    avail = S - 2 * pad
    if total > avail:
        f = avail / total
        els = [e.resize((max(1, int(e.size[0] * f)), max(1, int(e.size[1] * f))), Image.LANCZOS) for e in els]
        gap = int(gap * f)
        total = sum(e.size[1] for e in els) + gap * (len(els) - 1)
    y = (S - total) // 2
    for e in els:
        x = (S - e.size[0]) // 2
        canvas.paste(e, (x, y), e) if e.mode == "RGBA" else canvas.paste(e, (x, y))
        y += e.size[1] + gap
    canvas.save(out_path)
    return out_path

def verify(out, url):
    try:
        import cv2
        det = cv2.QRCodeDetector()
        img = cv2.imread(out)
        data, _, _ = det.detectAndDecode(img)
        if data == url:
            return "OK -> " + data
        # dark/inverted prints: OpenCV needs dark-on-light, so try the inverse.
        # A pass here means the code is structurally valid; phone cameras (iOS 11+,
        # Android/Lens) read inverted QR natively.
        data2, _, _ = det.detectAndDecode(cv2.bitwise_not(img))
        if data2 == url:
            return "OK (inverted) -> " + data2
        return f"WARNING decode mismatch: {data!r}"
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

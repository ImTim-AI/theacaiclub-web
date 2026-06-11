#!/usr/bin/env python3
"""TRUE-VECTOR PDF menu stands (print-shop ready) for The Acai Club.

Reproduces the dark `make_stand()` layout (see make-qr.py) as PURE VECTOR — no
raster anywhere:
  - QR modules as <rect>
  - the "THE ACAI CLUB" wordmark from brand/acai-club-logo.svg (vector paths, recoloured)
  - caption ("ORDER NOW" / "JOIN THE CLUB") as OUTLINED glyph paths
    (Montserrat SemiBold, instanced at wght=600 — no font dependency for the print shop)

Each store gets a 2-page PDF: page 1 ORDER NOW, page 2 JOIN THE CLUB, both pointing
at the same /qr/<slug> handle. SVGs are written too (one per face) for editing.

Run: cd theacaiclub/web && python3 qr/make-vector.py
Needs: qrcode, fonttools, opencv-python (verify), and `rsvg-convert` on PATH.
"""
import os, re, math, subprocess, tempfile
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..")
OUT = os.path.join(WEB, "qr_codes")
LOGO_SVG = os.path.join(WEB, "..", "brand", "acai-club-logo.svg")
MONT = os.path.join(HERE, "fonts", "Montserrat.ttf")

DARK_BG = "#1a1a1a"   # near-black canvas (black acrylic)
CREAM = "#f5f1ec"     # brand cream — the "light" ink on dark
BOX = 10              # SVG units per QR module

QR = "https://theacaiclub.com/qr"
STORES = [("datchet", "Datchet"), ("beaconsfield", "Beaconsfield"), ("reading", "Reading")]
FACES = [("", "ORDER NOW"), ("-flipside", "JOIN THE CLUB")]


# ---- logo (vector wordmark, recoloured to cream) ------------------------------
def logo_inner():
    """Return (inner_paths, vbw, vbh) from the brand wordmark SVG, fill recoloured."""
    svg = open(LOGO_SVG).read()
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    vbw, vbh = float(vb.group(1)), float(vb.group(2))
    g = re.search(r'(<g\s+transform="[^"]*"\s*\n?\s*fill="#000000"\s+stroke="none">.*?</g>)', svg, re.S)
    inner = g.group(1).replace('fill="#000000"', f'fill="{CREAM}"')
    return inner, vbw, vbh


# ---- caption (outlined glyphs, Montserrat SemiBold) ---------------------------
def caption_path(text, weight=600):
    """Outline `text` as a single SVG path (font units, y-up).
    Returns (path_d, minx, width, cap_h, descent_abs, upm)."""
    f = TTFont(MONT)
    if "fvar" in f:
        instancer.instantiateVariableFont(f, {"wght": weight}, inplace=True)
    upm = f["head"].unitsPerEm
    cap_h = getattr(f["OS/2"], "sCapHeight", None) or int(upm * 0.70)
    desc_abs = abs(f["hhea"].descent)
    cmap = f.getBestCmap()
    gs = f.getGlyphSet()
    hmtx = f["hmtx"]

    d, x = [], 0
    minx, maxx = 1e9, -1e9
    for ch in text:
        gname = cmap.get(ord(ch))
        if gname is None:
            x += int(upm * 0.3)
            continue
        pen = SVGPathPen(gs)
        # translate this glyph by current pen x
        from fontTools.pens.transformPen import TransformPen
        tpen = TransformPen(pen, (1, 0, 0, 1, x, 0))
        gs[gname].draw(tpen)
        seg = pen.getCommands()
        if seg:
            d.append(seg)
        adv = hmtx[gname][0]
        if ch != " ":
            minx = min(minx, x); maxx = max(maxx, x + adv)
        x += adv
    if minx > maxx:
        minx, maxx = 0, x
    return " ".join(d), minx, (maxx - minx), cap_h, desc_abs, upm


# ---- one face -> SVG string ---------------------------------------------------
def build_svg(url, caption, version):
    qr = qrcode.QRCode(version=version, error_correction=ERROR_CORRECT_H, box_size=BOX, border=4)
    qr.add_data(url); qr.make(fit=(version is None))
    m = qr.get_matrix()            # includes the 4-module quiet zone
    n = len(m)
    W = n * BOX

    inner, vbw, vbh = logo_inner()
    lkw = W * 0.26
    s_logo = lkw / vbw
    lkh = vbh * s_logo
    cx = cy = W / 2.0
    logox, logoy = cx - lkw / 2.0, cy - lkh / 2.0

    # centre plate (same colour as bg -> a clean hole under the wordmark)
    content_w, content_h = lkw, lkh
    margin = lkw * 0.09
    side = 2 * (math.hypot(content_w, content_h) / 2 + margin)

    # caption geometry (mirror make_stand: fixed letter height + band)
    pad_top, band_h, pad_bot = W * 0.04, W * 0.105, W * 0.07
    target_h, max_w = W * 0.105, W * 0.86
    totalH = W + pad_top + band_h + pad_bot

    d, minx, cw_u, cap_h, desc_abs, upm = caption_path(caption)
    block_h_u = cap_h + desc_abs                 # match label_block's cap+descent height
    s_txt = target_h / block_h_u
    if cw_u * s_txt > max_w:
        s_txt = max_w / cw_u
    capW = cw_u * s_txt
    band_cy = W + pad_top + band_h / 2.0
    baseline_y = band_cy + (cap_h * s_txt) / 2.0     # centre the caps in the band
    tx = (W - capW) / 2.0 - minx * s_txt

    # --- assemble ---
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{totalH:.2f}" '
        f'viewBox="0 0 {W} {totalH:.2f}">',
        f'<rect x="0" y="0" width="{W}" height="{totalH:.2f}" fill="{DARK_BG}"/>',
    ]
    # QR modules as ONE filled path (horizontal runs as rectangle subpaths) — a
    # single fill op means no anti-alias seams between abutting modules at print.
    runs = []
    for r, row in enumerate(m):
        c = 0
        while c < n:
            if row[c]:
                c0 = c
                while c < n and row[c]:
                    c += 1
                x, y, w = c0 * BOX, r * BOX, (c - c0) * BOX
                runs.append(f"M{x} {y}h{w}v{BOX}h{-w}z")
            else:
                c += 1
    parts.append(f'<path d="{"".join(runs)}" fill="{CREAM}"/>')
    # centre plate hole + wordmark
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{side/2:.2f}" fill="{DARK_BG}"/>')
    parts.append(f'<g transform="translate({logox:.2f},{logoy:.2f}) scale({s_logo:.6f})">{inner}</g>')
    # caption (outlined, y-up font space flipped to y-down)
    parts.append(f'<path transform="translate({tx:.2f},{baseline_y:.2f}) scale({s_txt:.6f},{-s_txt:.6f})" '
                 f'd="{d}" fill="{CREAM}"/>')
    parts.append('</svg>')
    return "\n".join(parts)


def svg_to_png(svg_path, png_path):
    subprocess.run(["rsvg-convert", "-f", "png", "-o", png_path, svg_path], check=True)


def svg_to_pdf(svg_paths, pdf_path):
    # rsvg-convert concatenates multiple inputs into a multi-page PDF
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", pdf_path, *svg_paths], check=True)


def verify(png, url):
    import cv2
    det = cv2.QRCodeDetector()
    img = cv2.imread(png)
    for im in (img, cv2.bitwise_not(img)):
        data, _, _ = det.detectAndDecode(im)
        if data == url:
            return True
    return False


def adaptive_svg(url, caption):
    """Pick the lowest QR version whose finished vector face still decodes."""
    tmp = os.path.join(tempfile.gettempdir(), "_vqr.svg")
    png = os.path.join(tempfile.gettempdir(), "_vqr.png")
    for v in [None] + list(range(2, 21)):
        try:
            svg = build_svg(url, caption, v)
        except qrcode.exceptions.DataOverflowError:
            continue
        open(tmp, "w").write(svg)
        svg_to_png(tmp, png)
        if verify(png, url):
            return svg
    return svg   # fallback


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for slug, _name in STORES:
        url = f"{QR}/{slug}"
        face_svgs = []
        for suffix, caption in FACES:
            svg = adaptive_svg(url, caption)
            svg_file = os.path.join(OUT, f"menu{suffix}-{slug}-dark.svg")
            open(svg_file, "w").write(svg)
            face_svgs.append(svg_file)
            print(f"  {os.path.basename(svg_file):34s} {caption}")
        pdf = os.path.join(OUT, f"menu-{slug}-dark.pdf")
        svg_to_pdf(face_svgs, pdf)
        # verify both rendered pages decode
        png = os.path.join(tempfile.gettempdir(), "_chk.png")
        ok = []
        for sf in face_svgs:
            svg_to_png(sf, png)
            ok.append("OK" if verify(png, url) else "FAIL")
        print(f"-> {os.path.basename(pdf):26s} vector, 2 pages, decode {ok}\n")

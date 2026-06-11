#!/usr/bin/env python3
"""Regenerate the full Acai Club QR set in the house style:
circular centre plate, NO icon, 2-line label under the wordmark (colour sampled
from the logo). Outputs to web/qr_codes/. Re-run: python3 qr/generate-all.py
"""
import os, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "qr_codes")
os.makedirs(OUT, exist_ok=True)

# load the engine (make-qr.py has a hyphen -> import via importlib)
spec = importlib.util.spec_from_file_location("mq", os.path.join(HERE, "make-qr.py"))
mq = importlib.util.module_from_spec(spec); spec.loader.exec_module(mq)

# Printed codes encode a STABLE /qr/<slug> handle; the destination is resolved by
# web/public/_redirects at scan time, so any code can be repointed later WITHOUT
# reprinting. Keep the slugs here in sync with _redirects. (Instagram stays a
# direct link — it's not an app-bound code we'd ever repoint.)
QR = "https://theacaiclub.com/qr"
IG = "https://www.instagram.com/channel/AbY12BpE6JQD6QOB/"

# name, url, two-line label.
SET = [
    ("app-download",        QR + "/app",          ["Download", "the App"]),
    ("runclub-instagram",   IG,                   ["Run Club", "Community"]),
    ("runclub-instagram-logo", IG,                None),  # logo-only (no inner label) — for poster composites w/ external caption
    ("app-runclub",         QR + "/run-club",     ["Run Club", "in the App"]),
    ("app-runclub-logo",    QR + "/run-club",     None),  # logo-only, repointable via _redirects (/qr/run-club)
    ("app-get-logo",        QR + "/app",          None),  # logo-only, repointable via _redirects (/qr/app -> /get)
    ("order-beaconsfield",  QR + "/beaconsfield", ["Order Now", "Beaconsfield"]),
    ("order-reading",       QR + "/reading",      ["Order Now", "Reading"]),
    ("order-datchet",       QR + "/datchet",      ["Order Now", "Datchet"]),
]

# Stand / menu posters: logo-only QR with the caption BELOW the code (taller image).
# dark=True -> light QR/logo/text on near-black, for printing on black acrylic.
# Both Datchet stand faces (and dark variants) resolve to the same /qr/datchet.
STANDS = [
    ("menu-datchet",               QR + "/datchet", ["ORDER NOW"],     False),
    ("menu-flipside-datchet",      QR + "/datchet", ["JOIN THE CLUB"], False),
    ("menu-datchet-dark",          QR + "/datchet", ["ORDER NOW"],     True),
    ("menu-flipside-datchet-dark", QR + "/datchet", ["JOIN THE CLUB"], True),
    ("menu-beaconsfield-dark",          QR + "/beaconsfield", ["ORDER NOW"],     True),
    ("menu-flipside-beaconsfield-dark", QR + "/beaconsfield", ["JOIN THE CLUB"], True),
    ("menu-reading-dark",          QR + "/reading", ["ORDER NOW"],     True),
    ("menu-flipside-reading-dark", QR + "/reading", ["JOIN THE CLUB"], True),
]

if __name__ == "__main__":
    for name, url, lines in SET:
        out = os.path.join(OUT, name + ".png")
        mq.make_circle(url, out, lines=lines, icon="none")
        print(f"{name:28s} {mq.verify(out, url)}")
    for name, url, lines, dark in STANDS:
        out = os.path.join(OUT, name + ".png")
        mq.make_stand(url, out, lines=lines, dark=dark)
        print(f"{name:28s} {mq.verify(out, url)}")

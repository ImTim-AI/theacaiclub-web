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

GET = "https://theacaiclub.com/get"
IG = "https://www.instagram.com/channel/AbY12BpE6JQD6QOB/"

# name, url, two-line label.
# Deep-link intent is carried in a single ?target= param (run-club / store slug),
# read by /get today (download) and by the app's deep-link handler later.
SET = [
    ("app-download",        GET,                          ["Download", "the App"]),
    ("runclub-instagram",   IG,                           ["Run Club", "Community"]),
    ("app-runclub",         GET + "?target=run-club",     ["Run Club", "in the App"]),
    ("order-beaconsfield",  GET + "?target=beaconsfield", ["Order Now", "Beaconsfield"]),
    ("order-reading",       GET + "?target=reading",      ["Order Now", "Reading"]),
    ("order-datchet",       GET + "?target=datchet",      ["Order Now", "Datchet"]),
]

# Stand / menu posters: logo-only QR with the caption BELOW the code (taller image).
# dark=True -> light QR/logo/text on near-black, for printing on black acrylic.
STANDS = [
    ("menu-datchet",               GET + "?target=datchet", ["ORDER NOW"],     False),
    ("menu-flipside-datchet",      GET + "?target=datchet", ["JOIN THE CLUB"], False),
    ("menu-datchet-dark",          GET + "?target=datchet", ["ORDER NOW"],     True),
    ("menu-flipside-datchet-dark", GET + "?target=datchet", ["JOIN THE CLUB"], True),
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

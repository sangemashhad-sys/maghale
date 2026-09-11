"""Scan local PDFs/TXTs for the numeric claims used in draft/section45_and_conclusion.md.

Usage: python evidence/scan_claims.py
Writes file, match, and surrounding context for each pattern to
evidence/_claims_report.txt. Output goes to a UTF-8 file rather than stdout
because the console codepage here (cp1256) cannot encode every character that
appears in the extracted text.
"""
import glob
import os
import re

import pymupdf

OUT = "evidence/_claims_report.txt"

PATTERNS = {
    # 10^3.5 -> 10^6.5 dipole-orientation Purcell swing (Barreda review, ref. 295)
    "orient_swing": r"10\s*3\.5|10\s*6\.5|103\.5|106\.5",
    # LDOS-based vs cavity-mode Purcell factor decoupling below ~5 nm
    "ldos_vs_cavity": r"(?:LDOS|local density).{0,120}cavity[- ]mode|cavity[- ]mode.{0,120}LDOS",
    # quantum efficiency ceiling of the all-plasmonic nanogap
    "qe_036": r"0\.36",
}


def read_text(path: str) -> str:
    if path.lower().endswith(".pdf"):
        try:
            with pymupdf.open(path) as doc:
                return "".join(page.get_text() for page in doc)
        except Exception as exc:  # unreadable/encrypted PDF
            return f"<<unreadable: {exc}>>"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError as exc:
        return f"<<unreadable: {exc}>>"


def main() -> None:
    files = sorted(
        p for p in glob.glob("**/*", recursive=True)
        if p.lower().endswith((".pdf", ".txt")) and os.path.isfile(p)
    )
    hits = 0
    with open(OUT, "w", encoding="utf-8") as out:
        out.write("scanned files: %d\n\n" % len(files))
        for path in files:
            text = read_text(path)
            for name, pattern in PATTERNS.items():
                for m in re.finditer(pattern, text, re.IGNORECASE):
                    hits += 1
                    start = max(0, m.start() - 350)
                    ctx = " ".join(text[start:m.end() + 250].split())
                    out.write("[%s] %s\n    %s\n\n" % (name, path, ctx))
        out.write("total hits: %d\n" % hits)
    print("written", OUT)


if __name__ == "__main__":
    main()

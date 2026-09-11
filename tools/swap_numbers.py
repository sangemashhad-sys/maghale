#!/usr/bin/env python3
"""One-shot number swap: superseded run -> pilot (later: pilot -> production).

Edit the MAP below for the production pass and re-run. Files are read/written
with newline='' so CRLF endings are preserved. Every replacement asserts its
expected count -- a mismatch aborts loudly instead of half-editing.
"""
import sys

FA143 = "۱۴۳"      # U+06F1 U+06F4 U+06F3
FA112 = "۱۱۲"      # U+06F1 U+06F1 U+06F2

# (file, old, new, expected_count)
MAP = [
    # ---- main.tex ----
    ("manuscript/main.tex", "(3D-FDTD)", "(axisymmetric FDTD)", 1),
    ("manuscript/main.tex", "3D-FDTD", "FDTD متقارن\u200cمحوری", 2),
    ("manuscript/main.tex", "ظاهری $7.1\\%$", "ظاهری $6.5\\%$", 1),
    ("manuscript/main.tex", "\\nm{607.9}", "\\nm{592}", 1),
    ("manuscript/main.tex", "2020.48", "1937", 1),
    ("manuscript/main.tex", FA143, FA112, 1),
    ("manuscript/main.tex", "143.42", "112.1", 1),
    ("manuscript/main.tex", "\\nm{615.1}", "\\nm{600}", 1),
    # ---- 01 ----
    ("manuscript/sections/01_introduction.tex", "سه\u200cبعدی FDTD",
     "FDTD متقارن\u200cمحوری", 1),
    # ---- 04 ----
    ("manuscript/sections/04_results.tex",
     "2020.48 - 143.42 = 1877.06", "1937 - 104.0 = 1833.0", 1),
    ("manuscript/sections/04_results.tex", "2020.48", "1937", 3),
    ("manuscript/sections/04_results.tex", "607.9", "592", 3),
    ("manuscript/sections/04_results.tex", "143.42", "112.1", 3),
    ("manuscript/sections/04_results.tex", "615.1", "600", 3),
    ("manuscript/sections/04_results.tex", "{7.2}", "{8}", 2),
    ("manuscript/sections/04_results.tex", "7.1", "5.4", 2),
    ("manuscript/sections/04_results.tex", "92.9", "94.6", 1),
    ("manuscript/sections/04_results.tex", "1877.06", "1833.0", 1),
    ("manuscript/sections/04_results.tex", FA143, FA112, 1),
    ("manuscript/sections/04_results.tex", "تقریبی $5.4\\%$",
     "تقریبی $5.4\\%$ در طول\u200cموج قله\u200cی پورسل ($\\nm{592}$) و "
     "$6.5\\%$ در طول\u200cموج قله\u200cی توان تابشی ($\\nm{600}$)", 1),
    ("manuscript/sections/04_results.tex", "تشدید پلاسمونی؛",
     "$\\nm{610}$ (نزدیک تشدید)؛", 1),
    # ---- 05 ----
    ("manuscript/sections/05_conclusion.tex", "2020.48", "1937", 1),
    ("manuscript/sections/05_conclusion.tex", "607.9", "592", 1),
    ("manuscript/sections/05_conclusion.tex", FA143, FA112, 1),
    ("manuscript/sections/05_conclusion.tex", "615.1", "600", 1),
    ("manuscript/sections/05_conclusion.tex", "7.1", "5.4", 2),
]

cache = {}


def get(path):
    if path not in cache:
        with open(path, encoding="utf-8", newline="") as fh:
            cache[path] = fh.read()
    return cache[path]


def main():
    for path, old, new, n in MAP:
        text = get(path)
        found = text.count(old)
        if found != n:
            sys.exit("ABORT: %s: pattern %r found %d times, expected %d"
                     % (path, old[:60], found, n))
        cache[path] = text.replace(old, new)
    for path, text in cache.items():
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        print("updated", path)


if __name__ == "__main__":
    main()

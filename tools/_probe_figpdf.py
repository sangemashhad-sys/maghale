"""Temporary probe: inventory the structure of the figure PDFs.

Answers: who produced them, are the curves vector paths or a raster image,
and what text (axis ticks) is available for calibrating page -> data coords.
"""
from __future__ import annotations

import json
import pathlib
import sys

import fitz  # PyMuPDF

FIG_DIR = pathlib.Path(r"D:\مقاله\manuscript\figures")
OUT = pathlib.Path(r"D:\مقاله\tools\_probe_figpdf.json")


def inventory(path: pathlib.Path) -> dict:
    doc = fitz.open(path)
    page = doc[0]
    drawings = page.get_drawings()
    n_pts = 0
    n_lines = 0
    n_curves = 0
    for d in drawings:
        for item in d["items"]:
            op = item[0]
            if op == "l":
                n_lines += 1
                n_pts += 2
            elif op == "c":
                n_curves += 1
                n_pts += 4
            elif op == "re":
                n_pts += 4
            elif op == "qu":
                n_pts += 4
    words = page.get_text("words")
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "metadata": {k: v for k, v in doc.metadata.items() if v},
        "page_rect": list(page.rect),
        "n_images": len(page.get_images(full=True)),
        "n_drawing_paths": len(drawings),
        "n_line_segments": n_lines,
        "n_bezier_segments": n_curves,
        "n_points_total": n_pts,
        "n_words": len(words),
        "words_sample": [
            {"text": w[4], "x0": round(w[0], 2), "y0": round(w[1], 2),
             "x1": round(w[2], 2), "y1": round(w[3], 2)}
            for w in words
        ],
        "longest_paths": sorted(
            (
                {
                    "n_items": len(d["items"]),
                    "type": d.get("type"),
                    "color": d.get("color"),
                    "fill": d.get("fill"),
                    "width": d.get("width"),
                    "rect": [round(v, 2) for v in d["rect"]],
                }
                for d in drawings
            ),
            key=lambda r: -r["n_items"],
        )[:8],
    }


def main() -> int:
    if not FIG_DIR.is_dir():
        print("figures dir not found:", FIG_DIR)
        return 1
    report = []
    for pdf in sorted(FIG_DIR.glob("*.pdf")):
        report.append(inventory(pdf))
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    for r in report:
        print("=" * 70)
        print(f"{r['file']}  ({r['bytes']} bytes)  page={[round(v,1) for v in r['page_rect']]}")
        print(f"  metadata      : {r['metadata']}")
        print(f"  raster images : {r['n_images']}")
        print(f"  vector paths  : {r['n_drawing_paths']}  "
              f"(lines={r['n_line_segments']}, beziers={r['n_bezier_segments']}, "
              f"points={r['n_points_total']})")
        print(f"  text words    : {r['n_words']}")
        print("  biggest paths :")
        for p in r["longest_paths"]:
            print(f"     items={p['n_items']:6d} type={p['type']} w={p['width']} "
                  f"color={p['color']} rect={p['rect']}")
    print("=" * 70)
    print("full dump ->", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())

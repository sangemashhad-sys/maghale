"""Temporary probe: recover curve vertices + axis geometry from the figure PDFs.

The figures are GL2PS/VTK vector exports with no text objects, so calibration
values must be read off a rendered image; this script extracts everything that
is machine-readable and renders PNGs for the tick labels.
"""
from __future__ import annotations

import csv
import pathlib
import sys

import fitz  # PyMuPDF

fitz.TOOLS.mupdf_display_errors(False)

FIG_DIR = pathlib.Path(r"D:\مقاله\manuscript\figures")
OUT_DIR = pathlib.Path(r"D:\مقاله\_probe")
TARGETS = ["Purcell_Spectrum.pdf", "radiated_power_T.pdf"]
ZOOM = 3.0


def path_vertices(items: list) -> list[tuple[float, float]]:
    """Flatten a PyMuPDF drawing item list into an ordered vertex list."""
    pts: list[tuple[float, float]] = []
    for item in items:
        op = item[0]
        if op == "l":
            p0, p1 = item[1], item[2]
            if not pts:
                pts.append((p0.x, p0.y))
            pts.append((p1.x, p1.y))
        elif op == "c":
            p0, _, _, p3 = item[1], item[2], item[3], item[4]
            if not pts:
                pts.append((p0.x, p0.y))
            pts.append((p3.x, p3.y))
        elif op == "re":
            r = item[1]
            pts.extend([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)])
    return pts


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    for name in TARGETS:
        pdf = FIG_DIR / name
        doc = fitz.open(pdf)
        page = doc[0]
        stem = pdf.stem

        pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), alpha=False)
        png = OUT_DIR / f"render_{stem}.png"
        pix.save(png)

        drawings = page.get_drawings()
        print("=" * 78)
        print(f"{name}: {len(drawings)} paths, render {pix.width}x{pix.height} -> {png.name}")
        rows = []
        for i, d in enumerate(drawings):
            verts = path_vertices(d["items"])
            rows.append((i, d.get("type"), d.get("color"), d.get("fill"),
                         d.get("width"), d["rect"], len(verts), verts))
        # report every stroked path and every path with a large vertex count
        print(f"{'idx':>4} {'type':>5} {'w':>6} {'n':>6}  color                rect")
        for i, typ, color, fill, width, rect, n, _ in rows:
            if typ != "f" or n > 300:
                c = "-" if color is None else ",".join(f"{v:.3f}" for v in color)
                print(f"{i:>4} {str(typ):>5} {str(round(width,2) if width else '-'):>6} {n:>6}  "
                      f"{c:<20} [{rect.x0:.1f},{rect.y0:.1f},{rect.x1:.1f},{rect.y1:.1f}]")

        csv_path = OUT_DIR / f"paths_{stem}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["path_idx", "type", "color", "width", "vx", "vy"])
            for i, typ, color, fill, width, rect, n, verts in rows:
                c = "" if color is None else "|".join(f"{v:.4f}" for v in color)
                for (vx, vy) in verts:
                    w.writerow([i, typ, c, width, f"{vx:.4f}", f"{vy:.4f}"])
        print(f"  vertices -> {csv_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

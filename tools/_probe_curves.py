"""Temporary probe: reassemble the plotted curve from the extracted vertices.

Checks sampling structure (uniform in wavelength vs uniform in frequency) and
locates the peak vertex in page coordinates, ready for axis calibration.
"""
from __future__ import annotations

import csv
import pathlib
import statistics
import sys

PROBE = pathlib.Path(r"D:\مقاله\_probe")
CURVE_COLOR = "0.3922|0.7098|0.9647"


def load_curve(stem: str) -> list[tuple[float, float]]:
    rows: list[tuple[int, float, float]] = []
    with (PROBE / f"paths_{stem}.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["color"] == CURVE_COLOR and r["type"] == "s":
                rows.append((int(r["path_idx"]), float(r["vx"]), float(r["vy"])))
    # order the sub-paths left to right by their minimum x, keep vertex order inside
    by_path: dict[int, list[tuple[float, float]]] = {}
    for idx, vx, vy in rows:
        by_path.setdefault(idx, []).append((vx, vy))
    ordered: list[tuple[float, float]] = []
    for idx in sorted(by_path, key=lambda k: min(p[0] for p in by_path[k])):
        seg = by_path[idx]
        if seg[0][0] > seg[-1][0]:
            seg = seg[::-1]
        ordered.extend(seg)
    return ordered


def report(stem: str) -> None:
    pts = load_curve(stem)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    print("=" * 78)
    print(f"{stem}: {len(pts)} curve vertices")
    print(f"  x span (page pt): {min(xs):.3f} .. {max(xs):.3f}")
    print(f"  y span (page pt): {min(ys):.3f} .. {max(ys):.3f}   (y grows downward)")
    imin = ys.index(min(ys))
    print(f"  topmost vertex (curve maximum): x={xs[imin]:.4f}  y={ys[imin]:.4f}  (index {imin})")
    print(f"  x monotone non-decreasing: {all(b >= a for a, b in zip(xs, xs[1:]))}")

    dedup = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - dedup[-1][0]) > 1e-9 or abs(p[1] - dedup[-1][1]) > 1e-9:
            dedup.append(p)
    print(f"  unique consecutive vertices: {len(dedup)}")

    dx = [b - a for a, b in zip([p[0] for p in dedup], [p[0] for p in dedup[1:]]) if b - a > 1e-9]
    if dx:
        print(f"  dx: n={len(dx)} min={min(dx):.4f} median={statistics.median(dx):.4f} "
              f"max={max(dx):.4f} mean={statistics.fmean(dx):.4f} "
              f"stdev={statistics.pstdev(dx):.4f}")
        print(f"  dx first 12 : {[round(v,3) for v in dx[:12]]}")
        print(f"  dx last 12  : {[round(v,3) for v in dx[-12:]]}")
    print(f"  first 6 vertices: {[(round(a,2), round(b,2)) for a, b in dedup[:6]]}")
    print(f"  last 6 vertices : {[(round(a,2), round(b,2)) for a, b in dedup[-6:]]}")

    out = PROBE / f"curve_{stem}.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["vx_pt", "vy_pt"])
        for a, b in dedup:
            w.writerow([f"{a:.5f}", f"{b:.5f}"])
    print(f"  clean polyline -> {out.name}")


def main() -> int:
    for stem in ("Purcell_Spectrum", "radiated_power_T"):
        report(stem)
    return 0


if __name__ == "__main__":
    sys.exit(main())

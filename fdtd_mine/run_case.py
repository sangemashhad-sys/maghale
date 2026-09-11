"""CLI driver: run one axisymmetric FDTD case and save spectra to .npz.

Examples:
  python3 run_case.py --case vacuum --dz 2.0 --out vac2.npz
  python3 run_case.py --case rod --dz 0.503597122 --out rod.npz --dlam 2
"""
import argparse
import numpy as np
from cyl_fdtd import (build_grid, dipole_node, mask_rod, mask_sphere, run,
                      save_npz)

DZ_PROD = 35.0 / 69.5   # 0.503597 nm: dipole exactly on-node


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", choices=["vacuum", "rod", "sphere"], required=True)
    ap.add_argument("--dz", type=float, default=2.0, help="cell size in nm")
    ap.add_argument("--zmax", type=float, default=500.0, help="half-domain in nm")
    ap.add_argument("--pml", type=float, default=40.0, help="PML thickness in nm")
    ap.add_argument("--box", type=float, default=150.0, help="flux box half-size in nm")
    ap.add_argument("--tmax", type=float, default=300.0, help="max sim time in fs")
    ap.add_argument("--shutoff", type=float, default=1e-5)
    ap.add_argument("--dlam", type=float, default=4.0, help="spectral step in nm")
    ap.add_argument("--lam0", type=float, default=500.0)
    ap.add_argument("--lam1", type=float, default=900.0)
    ap.add_argument("--nf", type=float, nargs="*", default=[610.0],
                    help="near-field map wavelengths in nm")
    ap.add_argument("--zs", type=float, default=35.0, help="dipole z in nm")
    ap.add_argument("--nf-box", type=float, default=120.0, help="NF window size in nm")
    ap.add_argument("--snap-z", action="store_true",
                    help="snap zs to nearest Ez node (for non-35nm sources)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    g = build_grid(dz_nm=a.dz, zmax_nm=a.zmax, pml_nm=a.pml, box_nm=a.box)
    zs = a.zs
    if a.snap_z:
        js0 = int(round((zs * 1e-9 + g["Zmax"]) / g["dz"] - 0.5))
        zs = (-g["Zmax"] + (js0 + 0.5) * g["dz"]) * 1e9
        print("snapped zs: %.2f -> %.4f nm" % (a.zs, zs))
    js = dipole_node(g, zs)
    print("grid: dz=%.4f nm Nr=%d Nz=%d dt=%.3e s" % (a.dz, g["Nr"], g["Nz"], g["dt"]))
    print("dipole @ z=%.3f nm (js=%d); box r=%.1f z=%.1f nm" % (
        zs, js, g["box_r"] * 1e9, g["box_z"] * 1e9))

    if a.case == "vacuum":
        mEr = np.zeros((g["Nr"], g["Nz"] + 1), bool)
        mEz = np.zeros((g["Nr"] + 1, g["Nz"]), bool)
    elif a.case == "rod":
        mEr, mEz = mask_rod(g)
    else:
        mEr, mEz = mask_sphere(g)
    # safety: no metal inside PML
    r_met = (np.arange(g["Nr"]) + 0.5) * g["dr"]
    z_met = -g["Zmax"] + np.arange(g["Nz"] + 1) * g["dz"]
    assert (r_met[mEr.any(axis=1)].max() < g["Rmax"] - a.pml * 1e-9
            if mEr.any() else True), "metal inside radial PML!"
    assert (np.abs(z_met[mEr.any(axis=0)]).max() < g["Zmax"] - a.pml * 1e-9
            if mEr.any() else True), "metal inside z PML!"

    lam = np.arange(a.lam0, a.lam1 + 0.5 * a.dlam, a.dlam)
    res = run(g, mEr, mEz, z_src_nm=zs, lam_nm=lam, lam_nf_nm=tuple(a.nf),
              t_max_fs=a.tmax, shutoff=a.shutoff, tag=a.case,
              nf_box_nm=a.nf_box)
    save_npz(a.out, res)
    print("saved", a.out)


if __name__ == "__main__":
    main()

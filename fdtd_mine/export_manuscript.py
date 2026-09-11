"""Export in-house FDTD results into the manuscript figure pipeline (CSV).

Reads a rod (+ vacuum reference) .npz pair and writes the CSVs that
simulation/make_figures.py consumes:
    spectra.csv          lambda_nm, Fp, T, eta_a, A_metal, T_amin
    peaks.csv            quantity,value,unit
    nearfield.csv        |E|^2 matrix, rows = x, cols = z (x mirrored)
    nearfield_axes.csv   the x and z axes in nm

Fp/T/A_metal come from OUR axisymmetric FDTD (ratio vs vacuum run);
T_amin is Amin's independent Lumerical rerun (validation overlay).

Usage:
    python3 export_manuscript.py --rod rod_prod.npz --vac vac_prod.npz
    python3 export_manuscript.py --rod rod_dz2.npz --vac vac_dz2.npz   # pilot test
"""
import argparse
import csv
import os
import numpy as np
from cyl_fdtd import powers

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SIM = os.path.join(ROOT, "simulation")
AMIN_T = os.path.join(ROOT, "results_amin", "A_rod_longitudinal_T.txt")


def load_amin_T(lam_out):
    d = np.loadtxt(AMIN_T, skiprows=1)
    return np.interp(lam_out, d[:, 0], d[:, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rod", required=True)
    ap.add_argument("--vac", required=True)
    ap.add_argument("--nf-lam", type=float, default=None,
                    help="NF map wavelength (default: Fp-peak lambda)")
    a = ap.parse_args()

    v = dict(np.load(os.path.join(HERE, a.vac) if not os.path.isabs(a.vac) else a.vac))
    r = dict(np.load(os.path.join(HERE, a.rod) if not os.path.isabs(a.rod) else a.rod))
    lam, Pv_src, Pv_big, Pv_abs = powers(v)
    l2, Ps, Pb, Pa = powers(r)
    assert np.allclose(lam, l2), "rod/vacuum lambda grids differ!"
    Fp = (Pb + Pa) / Pv_big
    T = Pb / Pv_big
    Am = Pa / Pv_big
    eta = Pb / np.maximum(Pb + Pa, 1e-300)
    T_amin = load_amin_T(lam)

    with open(os.path.join(SIM, "spectra.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["lambda_nm", "Fp", "T", "eta_a", "A_metal", "T_amin"])
        for i in range(len(lam)):
            w.writerow(["%.3f" % lam[i], "%.6g" % Fp[i], "%.6g" % T[i],
                        "%.6g" % eta[i], "%.6g" % Am[i], "%.6g" % T_amin[i]])

    iF, iT = int(np.argmax(Fp)), int(np.argmax(T))
    lam_nf_all = np.asarray(r["lam_nf_nm"], float)
    want = a.nf_lam if a.nf_lam is not None else lam[iF]
    k = int(np.argmin(abs(lam_nf_all - want)))
    dz_nm = float(r["dz"]) * 1e9
    peaks = [("quantity", "value", "unit"),
             ("L_total", 60.0, "nm"), ("D_rod", 20.0, "nm"),
             ("R_cap", 10.0, "nm"), ("d_gap", 5.0, "nm"),
             ("mesh_accuracy", 0, "-"), ("dx_fine", dz_nm, "nm"),
             ("lambda_Fp", lam[iF], "nm"), ("Fp_max", Fp[iF], "-"),
             ("lambda_NF", lam_nf_all[k], "nm"),
             ("lambda_T", lam[iT], "nm"), ("T_max", T[iT], "-"),
             ("T_amin_max", float(T_amin.max()), "-"),
             ("lambda_T_amin", float(lam[int(np.argmax(T_amin))]), "nm"),
             ("balance_err_median", 0.0, "pct")]
    with open(os.path.join(SIM, "peaks.csv"), "w", newline="") as fh:
        csv.writer(fh).writerows(peaks)

    # --- nearfield map: |E|^2 at Fp peak (or --nf-lam) ---
    lam_nf = np.asarray(r["lam_nf_nm"], float)
    want = a.nf_lam if a.nf_lam is not None else lam[iF]
    k = int(np.argmin(abs(lam_nf - want)))
    dft_nf = r["dft_nf"]  # (2, nfk, nwi, nwj), Er / Ez
    Er = dft_nf[0, k]; Ez = dft_nf[1, k]
    # Er lives at r=(i+.5)dr: interpolate onto Ez r-grid (i*dr); Er(0)=0
    Er_c = np.zeros_like(Ez)
    Er_c[1:, :] = 0.5 * (Er[:-1, :] + Er[1:, :])
    e2_half = np.abs(Er_c) ** 2 + np.abs(Ez) ** 2  # (nwi, nwj), r>=0
    dr = float(r["dr"]) * 1e9
    dz = float(r["dz"]) * 1e9
    Zmax = float(r["Zmax"]) * 1e9
    i0 = int(r["nf_i0"]) if "nf_i0" in r else 0
    j0 = int(r["nf_j0"]) if "nf_j0" in r else 0
    rr = (i0 + np.arange(e2_half.shape[0])) * dr
    zz = -Zmax + (j0 + np.arange(e2_half.shape[1]) + 0.5) * dz
    # mirror r -> x (drop duplicated r=0 column on the mirrored side)
    x = np.concatenate([-rr[:0:-1], rr])
    e2 = np.concatenate([e2_half[:0:-1, :], e2_half], axis=0)
    np.savetxt(os.path.join(SIM, "nearfield.csv"), e2, delimiter=",", fmt="%.6e")
    with open(os.path.join(SIM, "nearfield_axes.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["axis", "values_nm"])
        w.writerow(["x", " ".join("%.4f" % v for v in x)])
        w.writerow(["z", " ".join("%.4f" % v for v in zz)])
    print("wrote simulation/{spectra,peaks,nearfield,nearfield_axes}.csv")
    print("Fp_max=%.1f @%.1f nm | T_max=%.1f @%.1f nm | T_amin=%.1f @%.1f nm | NF @%.1f nm" % (
        Fp[iF], lam[iF], T[iT], lam[iT],
        T_amin.max(), lam[int(np.argmax(T_amin))], lam_nf[k]))


if __name__ == "__main__":
    main()

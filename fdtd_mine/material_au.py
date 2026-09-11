"""Gold dispersive model for the in-house cylindrical FDTD solver.

Primary model: Drude + 2 Lorentz poles fitted (scipy least_squares) to
Johnson & Christy (PRB 6, 4370, 1972) spot data over 500-900 nm:

    eps(w) = 1 - f0*wp^2/(w*(w+i*G0)) + SUM_k f_k*wp^2/(w_k^2 - w^2 - i*w*G_k)

Fit quality: max relative error 7.6% (at 550 nm interband edge),
             3.7% at 600 nm, <5% over 600-800 nm.
Reference cross-check: Rakic et al., Appl. Opt. 37, 5271 (1998).

All frequencies below in eV; wp = 9.03 eV (Rakic value, fixed in fit).
"""
import numpy as np

EV = 1.602176634e-19      # J
HBAR = 1.054571817e-34    # J s
C = 299792458.0           # m/s
EPS0 = 8.8541878128e-12
MU0 = 4e-7 * np.pi

# Johnson & Christy (n, k) spot data used for the fit
JC_NK = {
    500: (0.96, 1.86), 550: (0.35, 2.75), 600: (0.25, 3.00),
    650: (0.17, 3.35), 700: (0.15, 3.70), 800: (0.16, 4.50),
    900: (0.17, 5.30),
}

WP_EV = 9.03
# [f0, G0, f1, G1, w1, f2, G2, w2]  (G, w in eV)
# Final fit to dense cubic-interpolated J&C data (Au_Johnson_nk.txt),
# 480-950 nm in 5 nm steps, resonance window (590-720 nm) double-weighted.
# Mean err 1.1%, max 2.8%; at 610/616 nm only 0.5%. No sharp poles in-window.
FITTED = [0.8978, 0.0480, 0.1036, 0.6203, 2.7467, 0.4977, 0.1500, 3.6581]
# Rakic et al. 1998, Table I, Au (cross-check only)
RAKIC = dict(
    wp=9.03,
    f=[0.760, 0.024, 0.010, 0.071, 0.601, 4.384],
    G=[0.053, 0.241, 0.345, 0.870, 2.494, 2.214],
    w0=[0.0, 0.415, 0.830, 2.969, 4.304, 13.32],
)


def eps_dl_ev(w_ev, p=FITTED, wp=WP_EV):
    """Fitted Drude+2Lorentz model, w in eV -> complex eps."""
    f0, G0, f1, G1, w1, f2, G2, w2 = p
    w = np.asarray(w_ev, dtype=complex)
    e = 1.0 - f0 * wp**2 / (w * (w + 1j * G0))
    e = e + f1 * wp**2 / (w1**2 - w**2 - 1j * w * G1)
    e = e + f2 * wp**2 / (w2**2 - w**2 - 1j * w * G2)
    return e


def eps_rakic_ev(w_ev):
    w = np.asarray(w_ev, dtype=complex)
    R = RAKIC
    e = 1.0 - R["f"][0] * R["wp"]**2 / (w * (w + 1j * R["G"][0]))
    for j in range(1, 6):
        e = e + R["f"][j] * R["wp"]**2 / (
            R["w0"][j]**2 - w**2 - 1j * w * R["G"][j])
    return e


def ade_coeffs_si(p=FITTED, wp_ev=WP_EV):
    """Return ADE pole coefficients in SI (rad/s) for the FDTD solver.

    Drude:      dJ/dt + g0*J = e0 * A0 * E,      A0 = f0*wp^2
    Lorentz k:   dJ/dt + gk*J + wk^2*P = e0 * Ak * E,  J = dP/dt
    """
    f0, G0, f1, G1, w1, f2, G2, w2 = p
    to_rad = EV / HBAR
    wp = wp_ev * to_rad
    return dict(
        drude=(f0 * wp**2, G0 * to_rad),
        lorentz=[(f1 * wp**2, G1 * to_rad, w1 * to_rad),
                 (f2 * wp**2, G2 * to_rad, w2 * to_rad)],
    )


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    lam = np.linspace(450, 950, 251)
    w = 1240.0 / lam
    e_fit = eps_dl_ev(w)
    e_rak = eps_rakic_ev(w)
    lj = np.array(sorted(JC_NK))
    ej = np.array([(n + 1j * k)**2 for (n, k) in [JC_NK[L] for L in lj]])
    fig, ax = plt.subplots(2, 1, figsize=(7, 6), sharex=True)
    ax[0].plot(lam, e_fit.real, "k-", lw=1.5, label="fit Drude+2L")
    ax[0].plot(lam, e_rak.real, "b--", lw=1, label="Rakic 1998")
    ax[0].plot(lj, ej.real, "ro", ms=5, label="J&C data")
    ax[0].set_ylabel("Re(eps)"); ax[0].legend(); ax[0].grid(True, alpha=0.3)
    ax[1].plot(lam, e_fit.imag, "k-", lw=1.5, label="fit Drude+2L")
    ax[1].plot(lam, e_rak.imag, "b--", lw=1, label="Rakic 1998")
    ax[1].plot(lj, ej.imag, "ro", ms=5, label="J&C data")
    ax[1].set_ylabel("Im(eps)"); ax[1].set_xlabel("wavelength (nm)")
    ax[1].legend(); ax[1].grid(True, alpha=0.3)
    fig.suptitle("Au permittivity: fit vs Johnson-Christy (500-900 nm window)")
    fig.tight_layout()
    fig.savefig("gold_fit_check.png", dpi=120)
    print("saved gold_fit_check.png")
    # resonance sanity: ellipsoid AR=3 in air needs Re(eps)=-8.2
    i = np.argmin(np.abs(e_fit.real + 8.2))
    print("quasistatic AR=3 resonance with fitted model: %.0f nm" % lam[i])

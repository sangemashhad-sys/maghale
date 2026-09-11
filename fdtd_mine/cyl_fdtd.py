"""Axisymmetric (r,z) FDTD solver for m=0 fields (Er, Ez, Hphi).

Built for: z-directed dipole on the axis of an axisymmetric gold
nanostructure (rod with caps / sphere) -- i.e. cases A, B, D of the paper.
Case C (transverse dipole) is NOT axisymmetric and is not covered.

Physics:
  - Yee grid in (r,z), unsplit fields.
  - Stretched-coordinate PML via ADE memory terms (psi): reflectionless
    absorption for propagating AND evanescent waves (Berenger split-field
    was tried first and found to reflect ~20-40%: it damps E but not the
    H-half carrying the wave, and amplifies evanescent dipole near-fields).
  - Dispersive gold via ADE: 1 Drude + 2 Lorentz poles
    (see material_au.py; fitted to Johnson & Christy data).
  - Broadband z-current source (differentiated Gaussian) on axis.
  - On-the-fly DFT: source field (diagnostic), flux-box surfaces
    (P_src small box, P_big radiated box), E-field subgrid (P_abs in
    metal), and |E|^2 map planes (near field).

Conventions (SI units throughout):
  Er[i,j]  at r=(i+0.5)*dr, z=-Zmax+j*dz        (Nr, Nz+1)
  Ez[i,j]  at r=i*dr,       z=-Zmax+(j+0.5)*dz  (Nr+1, Nz)
  H[i,j]   at r=(i+0.5)*dr, z=-Zmax+(j+0.5)*dz  (Nr, Nz)
  Grid built so the dipole lands EXACTLY on an Ez node:
    dz = 35nm/(K+0.5), Zmax = M*dz  (integers K, M).
"""
import numpy as np
import numba
from material_au import ade_coeffs_si, EPS0, MU0, C


# --------------------------------------------------------------------------
# grid construction
# --------------------------------------------------------------------------

def build_grid(dz_nm=2.0, zmax_nm=250.0, pml_nm=40.0, box_nm=150.0):
    dz = dz_nm * 1e-9
    dr = dz
    Zmax = zmax_nm * 1e-9
    Nz = 2 * int(round(Zmax / dz))
    Zmax = Nz * dz / 2.0            # snap so z range is symmetric; Nz even keeps dipole on-node
    Nr = int(round(Zmax / dr))      # Rmax = Zmax (square half-domain)
    Rmax = Nr * dr
    dt = 0.95 * dz / (C * np.sqrt(2.0))

    g = dict(dz=dz, dr=dr, dt=dt, Nz=Nz, Nr=Nr, Zmax=Zmax, Rmax=Rmax)

    # --- SC-PML conductivity profiles (polynomial, m=3) -------------------
    # Stretched-coordinate PML: d/dx -> (1/sx) d/dx with sx = 1 + sig/(i.w.eps0).
    # Realized by ADE memory terms psi, one per stretched derivative:
    #   dpsi/dt + (sig/eps0).psi = -(sig/eps0).D   (D = unstretched derivative)
    # integrated exactly: psi <- b.psi + (b-1).D, b = exp(-(sig/eps0).dt).
    # Corrected derivative = D + psi. Where sig = 0: b = 1, psi = 0 (pure vacuum).
    m_pml, Rc = 3.0, 1e-7
    d_pml = pml_nm * 1e-9
    eta0 = np.sqrt(MU0 / EPS0)
    smax = -(m_pml + 1.0) * np.log(Rc) / (2.0 * eta0 * d_pml)

    def prof(x, xmax):
        # x: node coords (>=0 side); returns sigma (0 inside, ramp in PML)
        depth = np.maximum(0.0, x - (xmax - d_pml)) / d_pml
        return smax * depth**m_pml

    def b_of(sig):
        return np.exp(-(np.asarray(sig) * dt / EPS0))

    r_Ez = np.arange(Nr + 1) * dr                    # Ez r-nodes
    r_H = (np.arange(Nr) + 0.5) * dr                 # H r-nodes
    z_Er = -Zmax + np.arange(Nz + 1) * dz            # Er z-nodes
    z_H = -Zmax + (np.arange(Nz) + 0.5) * dz         # H z-nodes
    g["b_Ezr"] = b_of(prof(r_Ez, Rmax))              # (Nr+1,) radial PML for Ez-eq
    g["b_Hr"] = b_of(prof(r_H, Rmax))                # (Nr,)   radial PML for H-eq
    g["b_Erz"] = b_of(prof(np.abs(z_Er), Zmax))      # (Nz+1,) axial PML for Er-eq
    g["b_Hz"] = b_of(prof(np.abs(z_H), Zmax))        # (Nz,)   axial PML for H-eq

    # --- flux-box planes (snapped to grid, recorded exactly) --------------
    box = box_nm * 1e-9
    iRB = int(round(box / dr))          # side plane at r = iRB*dr (Ez plane)
    jZB = int(round(box / dz))          # disk planes at z = +/-jZB*dz (Er plane)
    g["iRB"] = iRB
    g["jZ_top"] = Nz // 2 + jZB
    g["jZ_bot"] = Nz // 2 - jZB
    g["box_r"] = iRB * dr
    g["box_z"] = jZB * dz
    return g


def dipole_node(g, z_src_nm=35.0):
    """Ez node index (0, js) closest to z_src; asserts exact landing."""
    z_src = z_src_nm * 1e-9
    js = int(round((z_src + g["Zmax"]) / g["dz"] - 0.5))
    z_actual = -g["Zmax"] + (js + 0.5) * g["dz"]
    assert abs(z_actual - z_src) < 1e-12, "dipole off-grid by %g nm" % (
        abs(z_actual - z_src) * 1e9)
    return js


# --------------------------------------------------------------------------
# metal masks (staircase per E-component)
# --------------------------------------------------------------------------

def mask_rod(g):
    """60x20 nm rod: body |z|<=20nm + caps R=10 at z=+-20nm. Returns mEr, mEz."""
    dr, dz, Zmax, Nr, Nz = g["dr"], g["dz"], g["Zmax"], g["Nr"], g["Nz"]
    R = 10e-9
    zc = 20e-9
    rEr = (np.arange(Nr) + 0.5) * dr
    zEr = -Zmax + np.arange(Nz + 1) * dz
    rEz = np.arange(Nr + 1) * dr
    zEz = -Zmax + (np.arange(Nz) + 0.5) * dz

    def inside(r, z):
        rr = np.asarray(r)[:, None]
        zz = np.asarray(z)[None, :]
        body = (rr <= R) & (np.abs(zz) <= zc)
        cap = (rr**2 + (np.abs(zz) - zc)**2 <= R**2)
        return body | cap

    mEr = inside(rEr, zEr)
    mEz = inside(rEz, zEz)
    return mEr, mEz


def mask_sphere(g, R_nm=15.874):
    R = R_nm * 1e-9
    dr, dz, Zmax, Nr, Nz = g["dr"], g["dz"], g["Zmax"], g["Nr"], g["Nz"]
    rEr = (np.arange(Nr) + 0.5) * dr
    zEr = -Zmax + np.arange(Nz + 1) * dz
    rEz = np.arange(Nr + 1) * dr
    zEz = -Zmax + (np.arange(Nz) + 0.5) * dz

    def inside(r, z):
        rr = np.asarray(r)[:, None]
        zz = np.asarray(z)[None, :]
        return rr**2 + zz**2 <= R**2

    return inside(rEr, zEr), inside(rEz, zEz)


# --------------------------------------------------------------------------
# numba kernels
# --------------------------------------------------------------------------

@numba.njit
def step_H(H, Er, Ez, b_Hr, b_Hz, psi_Hr, psi_Hz, dr, dz, dt):
    mu0 = 4e-7 * np.pi
    Nr, Nz = H.shape
    c = dt / mu0
    for i in range(Nr):
        for j in range(Nz):
            dEz_dr = (Ez[i + 1, j] - Ez[i, j]) / dr
            dEr_dz = (Er[i, j + 1] - Er[i, j]) / dz
            psi_Hr[i, j] = b_Hr[i] * psi_Hr[i, j] + (b_Hr[i] - 1.0) * dEz_dr
            psi_Hz[i, j] = b_Hz[j] * psi_Hz[i, j] + (b_Hz[j] - 1.0) * dEr_dz
            H[i, j] += c * ((dEz_dr + psi_Hr[i, j]) - (dEr_dz + psi_Hz[i, j]))


@numba.njit
def step_E(Er, Ez, H, b_Erz, b_Ezr, psi_Erz, psi_Ezr, dr, dz,
           mEr, mEz, JDr, JDz, JLr, JLz, PLr, PLz,
           A0, g0, A1, g1, w1, A2, g2, w2, dt):
    Nr, Nzp1 = Er.shape
    Nz = Nzp1 - 1
    e0 = 8.8541878128e-12
    # ADE coefficients (pole p: J half-step, P full-step)
    cJ0 = (1 - g0 * dt / 2) / (1 + g0 * dt / 2)
    cE0 = e0 * A0 * dt / (1 + g0 * dt / 2)
    cJ1 = (1 - g1 * dt / 2) / (1 + g1 * dt / 2)
    cP1 = -w1 * w1 * dt / (1 + g1 * dt / 2)
    cE1 = e0 * A1 * dt / (1 + g1 * dt / 2)
    cJ2 = (1 - g2 * dt / 2) / (1 + g2 * dt / 2)
    cP2 = -w2 * w2 * dt / (1 + g2 * dt / 2)
    cE2 = e0 * A2 * dt / (1 + g2 * dt / 2)

    # --- Er update (j=1..Nz-1 interior; edges stay 0 = PEC) ---
    for i in range(Nr):
        for j in range(1, Nz):
            curl = -(H[i, j] - H[i, j - 1]) / dz
            E = Er[i, j]
            if mEr[i, j]:
                Jd = JDr[i, j]
                J1 = JLr[0, i, j]
                J2 = JLr[1, i, j]
                Jd = cJ0 * Jd + cE0 * E
                J1 = cJ1 * J1 + cP1 * PLr[0, i, j] + cE1 * E
                J2 = cJ2 * J2 + cP2 * PLr[1, i, j] + cE2 * E
                PLr[0, i, j] += dt * J1
                PLr[1, i, j] += dt * J2
                JDr[i, j] = Jd
                JLr[0, i, j] = J1
                JLr[1, i, j] = J2
                Er[i, j] = E + (dt / e0) * curl - (dt / e0) * (Jd + J1 + J2)
            else:
                psi_Erz[i, j] = (b_Erz[j] * psi_Erz[i, j]
                                 + (b_Erz[j] - 1.0) * curl)
                Er[i, j] = E + (dt / e0) * (curl + psi_Erz[i, j])
    # --- Ez update (i=0..Nr-1; i=Nr edge stays 0) ---
    for i in range(Nr):
        for j in range(Nz):
            if i == 0:
                # axis: (1/r)d(rH)/dr -> 4*H[0,j]/dr
                curl = 4.0 * H[0, j] / dr
            else:
                rp = (i + 0.5) * dr
                rm = (i - 0.5) * dr
                r0 = i * dr
                curl = (rp * H[i, j] - rm * H[i - 1, j]) / (dr * r0)
            E = Ez[i, j]
            if mEz[i, j]:
                Jd = JDz[i, j]
                J1 = JLz[0, i, j]
                J2 = JLz[1, i, j]
                Jd = cJ0 * Jd + cE0 * E
                J1 = cJ1 * J1 + cP1 * PLz[0, i, j] + cE1 * E
                J2 = cJ2 * J2 + cP2 * PLz[1, i, j] + cE2 * E
                PLz[0, i, j] += dt * J1
                PLz[1, i, j] += dt * J2
                JDz[i, j] = Jd
                JLz[0, i, j] = J1
                JLz[1, i, j] = J2
                Ez[i, j] = E + (dt / e0) * curl - (dt / e0) * (Jd + J1 + J2)
            else:
                psi_Ezr[i, j] = (b_Ezr[i] * psi_Ezr[i, j]
                                 + (b_Ezr[i] - 1.0) * curl)
                Ez[i, j] = E + (dt / e0) * (curl + psi_Ezr[i, j])


@numba.njit
def accum_src(dft_Esrc, dft_Jsrc, Ez_src, Jsrc, om, t_now, wsum):
    for k in range(om.shape[0]):
        ph = np.cos(om[k] * t_now) + 1j * np.sin(om[k] * t_now)
        dft_Esrc[k] += Ez_src * ph * wsum
        dft_Jsrc[k] += Jsrc * ph * wsum


@numba.njit
def accum_plane(dft_e, dft_h, Er, Ez, H, om, t_now, wsum,
                iRB, jZt, jZb, Nr, Nz):
    # side plane r=iRB*dr + disk planes z=+-jZB*dz of one closed box
    for k in range(om.shape[0]):
        ph = np.cos(om[k] * t_now) + 1j * np.sin(om[k] * t_now)
        for j in range(Nz):
            ez = Ez[iRB, j]
            h = 0.5 * (H[iRB - 1, j] + H[iRB, j])
            dft_e[0, k, j] += ez * ph * wsum
            dft_h[0, k, j] += h * ph * wsum
        for i in range(Nr):
            er_t = Er[i, jZt]
            h_t = 0.5 * (H[i, jZt - 1] + H[i, jZt])
            er_b = Er[i, jZb]
            h_b = 0.5 * (H[i, jZb - 1] + H[i, jZb])
            dft_e[1, k, i] += er_t * ph * wsum
            dft_h[1, k, i] += h_t * ph * wsum
            dft_e[2, k, i] += er_b * ph * wsum
            dft_h[2, k, i] += h_b * ph * wsum


@numba.njit
def accum_flux(dft, Er, Ez, H, om, t_now, wsum,
               iRB, jZt, jZb, iRB2, jZt2, jZb2, Nr, Nz):
    # slots 0..5: big (radiated-power) box; slots 6..11: small (source) box
    accum_plane(dft[0:3], dft[3:6], Er, Ez, H, om, t_now, wsum,
                iRB, jZt, jZb, Nr, Nz)
    accum_plane(dft[6:9], dft[9:12], Er, Ez, H, om, t_now, wsum,
                iRB2, jZt2, jZb2, Nr, Nz)


@numba.njit
def accum_nf(dft_nf, Er, Ez, om_nf, t_now, wsum, i0, j0):
    # dft_nf[comp(0=Er,1=Ez), k, ii, jj] on window i0.., j0.. (Ez-indexed);
    # Er (Nr,Nz+1) sampled at j+1 to align z with Ez plane j.
    _, nfk, nwi, nwj = dft_nf.shape
    for k in range(nfk):
        ph = np.cos(om_nf[k] * t_now) + 1j * np.sin(om_nf[k] * t_now)
        for ii in range(nwi):
            for jj in range(nwj):
                i = i0 + ii
                j = j0 + jj
                dft_nf[0, k, ii, jj] += Er[i, j + 1] * ph * wsum
                dft_nf[1, k, ii, jj] += Ez[i, j] * ph * wsum


@numba.njit
def accum_abs(dft_abs, Er, Ez, om, t_now, wsum, jc, jA, iA):
    # E-field DFT on a subgrid around the origin (for P_abs in metal).
    for k in range(om.shape[0]):
        ph = np.cos(om[k] * t_now) + 1j * np.sin(om[k] * t_now)
        for i in range(iA):
            for jj in range(2 * jA + 1):
                j = jc - jA + jj
                dft_abs[0, k, i, jj] += Er[i, j] * ph * wsum
                dft_abs[1, k, i, jj] += Ez[i, j] * ph * wsum


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def src_pulse(t, tau=0.7e-15, t0=None):
    if t0 is None:
        t0 = 5 * tau
    x = (t - t0) / tau
    return x * np.exp(-x * x)


def run(g, mEr, mEz, z_src_nm=35.0, lam_nm=None, lam_nf_nm=(610.0,),
        t_max_fs=300.0, shutoff=1e-5, sub_flux=1, sub_nf=2,
        verbose=True, tag="run", src="pulse", cw_lam_nm=700.0,
        dft_t0_fs=0.0, nf_box_nm=120.0):
    dz, dr, dt = g["dz"], g["dr"], g["dt"]
    Nr, Nz = g["Nr"], g["Nz"]
    if lam_nm is None:
        lam_nm = np.arange(500, 901, 4)
    lam_nm = np.asarray(lam_nm, float)
    om = 2 * np.pi * C / (lam_nm * 1e-9)
    om_nf = 2 * np.pi * C / (np.asarray(lam_nf_nm, float) * 1e-9)

    Er = np.zeros((Nr, Nz + 1))
    Ez = np.zeros((Nr + 1, Nz))
    H = np.zeros((Nr, Nz))
    psi_Erz = np.zeros((Nr, Nz + 1))
    psi_Ezr = np.zeros((Nr + 1, Nz))
    psi_Hr = np.zeros((Nr, Nz))
    psi_Hz = np.zeros((Nr, Nz))
    JDr = np.zeros((Nr, Nz + 1))
    JDz = np.zeros((Nr + 1, Nz))
    JLr = np.zeros((2, Nr, Nz + 1))
    JLz = np.zeros((2, Nr + 1, Nz))
    PLr = np.zeros((2, Nr, Nz + 1))
    PLz = np.zeros((2, Nr + 1, Nz))

    ade = ade_coeffs_si()
    A0, g0 = ade["drude"]
    (A1, g1, w1), (A2, g2, w2) = ade["lorentz"]

    js = dipole_node(g, z_src_nm)
    dV = np.pi * (dr / 2.0)**2 * dz     # ring-0 cell volume (r=0 source)

    # small source box: radius ~4 nm, z faces +-1.5*dz from source node
    iRB2 = max(2, int(round(4e-9 / dr)))
    jZt2 = js + 2
    jZb2 = js - 1
    assert iRB2 < Nr and jZt2 < Nz and jZb2 >= 1
    rB2 = iRB2 * dr
    nfk_sur = max(Nz, Nr)
    dft = np.zeros((12, len(om), nfk_sur), dtype=complex)
    dft_Esrc = np.zeros(len(om), dtype=complex)
    dft_Jsrc = np.zeros(len(om), dtype=complex)
    # NF window around origin: |r|,|z| <= nf_box/2
    nfw = (nf_box_nm * 1e-9) / 2.0
    i0 = 0
    i1 = min(Nr, int(np.ceil(nfw / dr)) + 1)
    j0 = max(0, Nz // 2 - int(np.ceil(nfw / dz)) - 1)
    j1 = min(Nz, Nz // 2 + int(np.ceil(nfw / dz)) + 1)
    dft_nf = np.zeros((2, len(om_nf), i1 - i0, j1 - j0), dtype=complex)
    # P_abs subgrid around origin: r < ~14 nm, |z| < ~34 nm (covers rod+sphere)
    jc = Nz // 2
    jA = int(np.ceil(34e-9 / dz)) + 1
    iA = int(np.ceil(14e-9 / dr)) + 1
    assert jc - jA >= 1 and jc + jA <= Nz - 1 and iA <= Nr
    dft_abs = np.zeros((2, len(om), iA, 2 * jA + 1), dtype=complex)

    n_max = int(t_max_fs * 1e-15 / dt)
    tau, t0 = 0.7e-15, 5 * 0.7e-15
    epeak = 0.0
    stop_step = n_max
    import time
    t_start = time.time()
    for n in range(n_max):
        step_H(H, Er, Ez, g["b_Hr"], g["b_Hz"], psi_Hr, psi_Hz, dr, dz, dt)
        step_E(Er, Ez, H, g["b_Erz"], g["b_Ezr"], psi_Erz, psi_Ezr,
               dr, dz, mEr, mEz, JDr, JDz, JLr, JLz, PLr, PLz,
               A0, g0, A1, g1, w1, A2, g2, w2, dt)
        tE = (n + 1) * dt
        if src == "cw":
            w0 = 2 * np.pi * C / (cw_lam_nm * 1e-9)
            T0 = 2 * np.pi / w0
            Tramp = 5 * T0
            ramp = 0.5 - 0.5 * np.cos(np.pi * min(tE / Tramp, 1.0))
            Jt = ramp * np.sin(w0 * tE)
        else:
            Jt = src_pulse(tE, tau, t0)
        if n % sub_flux == 0 and tE >= dft_t0_fs * 1e-15:
            # midpoint E (pre-injection minus half the soft-source kick):
            # this is the field the current does work against (trapezoidal).
            Ez_mid = Ez[0, js] - 0.5 * (dt / EPS0) * Jt
            accum_src(dft_Esrc, dft_Jsrc, Ez_mid, Jt, om, tE, sub_flux * dt)
            accum_flux(dft, Er, Ez, H, om, tE, sub_flux * dt,
                       g["iRB"], g["jZ_top"], g["jZ_bot"],
                       iRB2, jZt2, jZb2, Nr, Nz)
            accum_abs(dft_abs, Er, Ez, om, tE, sub_flux * dt, jc, jA, iA)
        Ez[0, js] -= (dt / EPS0) * Jt
        if n % sub_nf == 0 and tE >= dft_t0_fs * 1e-15:
            accum_nf(dft_nf, Er, Ez, om_nf, tE, sub_nf * dt, i0, j0)
        if n % 500 == 0:
            emax = float(np.max(np.abs(Ez)) + np.max(np.abs(Er)))
            if emax > epeak:
                epeak = emax
            elif epeak > 0 and tE > t0 + 20 * tau and emax < shutoff * epeak:
                stop_step = n
                break
    wall = time.time() - t_start
    if verbose:
        print("[%s] steps=%d/%d (%.1f fs sim, %.1f s wall)" % (
            tag, stop_step, n_max, stop_step * dt * 1e15, wall))

    out = dict(lam_nm=lam_nm, lam_nf_nm=np.asarray(lam_nf_nm, float),
               dft=dft, dft_Esrc=dft_Esrc, dft_Jsrc=dft_Jsrc, dft_nf=dft_nf,
               dft_abs=dft_abs, mEr=mEr, mEz=mEz,
               abs_jc=jc, abs_jA=jA, abs_iA=iA,
               nf_i0=i0, nf_i1=i1, nf_j0=j0, nf_j1=j1,
               dV=dV, js=js, steps=stop_step, dt=dt,
               box_r=g["box_r"], box_z=g["box_z"],
               iRB=g["iRB"], jZt=g["jZ_top"], jZb=g["jZ_bot"],
               iRB2=iRB2, jZt2=jZt2, jZb2=jZb2, box_r2=rB2,
               dz=dz, dr=dr, Nr=Nr, Nz=Nz, Zmax=g["Zmax"])
    return out


def _box_power(dft6, Rb, iRB, jZb, jZt, dr, dz, Nr, h_phase):
    """Closed-surface flux from 6 slots [sideE, topE, botE, sideH, topH, botH].
    h_phase[k] = exp(-i*om*dt/2): time-centers H (sampled dt/2 before E)."""
    Ez_s = dft6[0][:, jZb:jZt]
    H_s = dft6[3][:, jZb:jZt] * h_phase[:, None]
    Pside = 0.5 * np.real(-Ez_s * np.conj(H_s)).sum(axis=1) * (2 * np.pi * Rb * dz)
    r_nodes = (np.arange(Nr) + 0.5) * dr
    w = 2 * np.pi * r_nodes * dr
    wbox = w[:iRB]
    Er_t = dft6[1][:, :iRB]
    H_t = dft6[4][:, :iRB] * h_phase[:, None]
    Ptop = 0.5 * (np.real(Er_t * np.conj(H_t)) * wbox[None, :]).sum(axis=1)
    Er_b = dft6[2][:, :iRB]
    H_b = dft6[5][:, :iRB] * h_phase[:, None]
    Pbot = -0.5 * (np.real(Er_b * np.conj(H_b)) * wbox[None, :]).sum(axis=1)
    return Pside + Ptop + Pbot


def eps_gold_im(om):
    """Im(eps) of the fitted Drude+2Lorentz gold model (exact for the ADE)."""
    from material_au import ade_coeffs_si
    ade = ade_coeffs_si()
    A0, g0 = ade["drude"]
    (A1, g1, w1), (A2, g2, w2) = ade["lorentz"]
    w = np.asarray(om, float)
    im = A0 * w * g0 / (w**4 + w**2 * g0**2)
    im = im + A1 * w * g1 / ((w1**2 - w**2)**2 + w**2 * g1**2)
    im = im + A2 * w * g2 / ((w2**2 - w**2)**2 + w**2 * g2**2)
    return im


def powers(res):
    """(lam, P_src, P_big, P_abs): source-box, big-box flux, metal absorption.

    P_tot = P_big + P_abs. J.E and the tiny source box are recorded but not
    used for physics (reactive-field cancellation makes them unreliable).
    """
    from material_au import EPS0, C
    dft = res["dft"]
    lam = res["lam_nm"]
    dr, dz = float(res["dr"]), float(res["dz"])
    dt = float(res["dt"])
    Nr = int(res["Nr"])
    om = 2 * np.pi * C / (np.asarray(lam, float) * 1e-9)
    h_phase = np.exp(-1j * om * dt / 2.0)
    P_big = _box_power(dft[0:6], float(res["box_r"]), int(res["iRB"]),
                       int(res["jZb"]), int(res["jZt"]), dr, dz, Nr, h_phase)
    P_src = _box_power(dft[6:12], float(res["box_r2"]), int(res["iRB2"]),
                       int(res["jZb2"]), int(res["jZt2"]), dr, dz, Nr, h_phase)
    # P_abs = sum_metal 0.5*om*eps0*Im(eps)*|E|^2*dV_cell
    jc, jA, iA = int(res["abs_jc"]), int(res["abs_jA"]), int(res["abs_iA"])
    mEr = np.asarray(res["mEr"])[:iA, jc - jA:jc + jA + 1]
    mEz = np.asarray(res["mEz"])[:iA, jc - jA:jc + jA + 1]
    Er2 = np.abs(res["dft_abs"][0][:, :iA, :])**2
    Ez2 = np.abs(res["dft_abs"][1][:, :iA, :])**2
    sig = om * EPS0 * eps_gold_im(om)   # effective conductivity (A/V/m)
    vEr = (2 * np.pi * (np.arange(iA) + 0.5) * dr * dr * dz)[None, :, None]
    vEz = (2 * np.pi * np.arange(iA) * dr * dr * dz)[None, :, None]
    vEz[0, 0, :] = np.pi * (dr / 2.0)**2 * dz   # on-axis ring volume
    P_abs = (0.5 * sig
             * (((Er2 * vEr * mEr[None]).sum(axis=(1, 2))
                + (Ez2 * vEz * mEz[None]).sum(axis=(1, 2)))))
    return lam, P_src, P_big, P_abs


def save_npz(path, res):
    np.savez_compressed(path, **{k: v for k, v in res.items()
                                 if isinstance(v, np.ndarray)},
                        steps=res["steps"], dt=res["dt"], dV=res["dV"],
                        js=res["js"], box_r=res["box_r"], box_z=res["box_z"],
                        iRB=res["iRB"], jZt=res["jZt"], jZb=res["jZb"],
                        iRB2=res["iRB2"], jZt2=res["jZt2"], jZb2=res["jZb2"],
                        box_r2=res["box_r2"],
                        abs_jc=res["abs_jc"], abs_jA=res["abs_jA"],
                        abs_iA=res["abs_iA"],
                        nf_i0=res["nf_i0"], nf_i1=res["nf_i1"],
                        nf_j0=res["nf_j0"], nf_j1=res["nf_j1"],
                        dz=res["dz"], dr=res["dr"], Nr=res["Nr"], Nz=res["Nz"],
                        Zmax=res["Zmax"])

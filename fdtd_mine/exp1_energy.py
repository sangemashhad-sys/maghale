"""EXP1: time-domain total-energy balance in vacuum (no DFT involved).

Compares, over a complete run to 30 fs:
  W_flux = sum_t S_box(t)*dt   (instantaneous Poynting flux, time domain)
  W_lar  = (mu0*dV^2/6pi c) * int (dJ/dt)^2 dt  (exact Larmor energy, no DFT)

Regression keeper: the FDTD core (without PML subtleties) must give
W_flux/W_lar = 1 to ~1% (residual = H half-step stagger, 1st order in dt).
"""
import numpy as np
from cyl_fdtd import build_grid, dipole_node, step_H, step_E, src_pulse
from material_au import ade_coeffs_si, EPS0, MU0, C

g = build_grid(dz_nm=2.0, zmax_nm=250.0, pml_nm=40.0, box_nm=150.0)
Nr, Nz, dr, dz, dt = g["Nr"], g["Nz"], g["dr"], g["dz"], g["dt"]
Er = np.zeros((Nr, Nz + 1))
Ez = np.zeros((Nr + 1, Nz))
H = np.zeros((Nr, Nz))
psi_Erz = np.zeros((Nr, Nz + 1))
psi_Ezr = np.zeros((Nr + 1, Nz))
psi_Hr = np.zeros((Nr, Nz))
psi_Hz = np.zeros((Nr, Nz))
mEr = np.zeros((Nr, Nz + 1), bool)
mEz = np.zeros((Nr + 1, Nz), bool)
JDr = np.zeros((Nr, Nz + 1)); JDz = np.zeros((Nr + 1, Nz))
JLr = np.zeros((2, Nr, Nz + 1)); JLz = np.zeros((2, Nr + 1, Nz))
PLr = np.zeros((2, Nr, Nz + 1)); PLz = np.zeros((2, Nr + 1, Nz))
ade = ade_coeffs_si()
A0, g0 = ade["drude"]
(A1, g1, w1), (A2, g2, w2) = ade["lorentz"]
js = dipole_node(g, 35.0)
dV = np.pi * (dr / 2.0) ** 2 * dz
tau, t0 = 0.7e-15, 5 * 0.7e-15

iRB, jZt, jZb = g["iRB"], g["jZ_top"], g["jZ_bot"]
Rb = g["box_r"]
w_disk = 2 * np.pi * (np.arange(iRB) + 0.5) * dr * dr

W_flux = 0.0
J_hist = []
n_max = int(30e-15 / dt)
for n in range(n_max):
    step_H(H, Er, Ez, g["b_Hr"], g["b_Hz"], psi_Hr, psi_Hz, dr, dz, dt)
    step_E(Er, Ez, H, g["b_Erz"], g["b_Ezr"], psi_Erz, psi_Ezr,
           dr, dz, mEr, mEz, JDr, JDz, JLr, JLz, PLr, PLz,
           A0, g0, A1, g1, w1, A2, g2, w2, dt)
    tE = (n + 1) * dt
    Jt = src_pulse(tE, tau, t0)
    J_hist.append(Jt)
    Ez[0, js] -= (dt / EPS0) * Jt
    # instantaneous box flux (H half-step behind E: 1st-order in dt, fine here)
    S_side = (-Ez[iRB, jZb:jZt]
              * 0.5 * (H[iRB - 1, jZb:jZt] + H[iRB, jZb:jZt])).sum() * (2 * np.pi * Rb * dz)
    S_top = (Er[:iRB, jZt] * 0.5 * (H[:iRB, jZt - 1] + H[:iRB, jZt]) * w_disk).sum()
    S_bot = -(Er[:iRB, jZb] * 0.5 * (H[:iRB, jZb - 1] + H[:iRB, jZb]) * w_disk).sum()
    W_flux += (S_side + S_top + S_bot) * dt

J_hist = np.array(J_hist)
dJdt = np.gradient(J_hist, dt)
W_lar = (MU0 * dV ** 2 / (6 * np.pi * C)) * (dJdt ** 2).sum() * dt

print("W_flux = %.6e" % W_flux)
print("W_lar  = %.6e" % W_lar)
print("W_flux/W_lar = %.4f  (want 1.00 +- 0.01)" % (W_flux / W_lar))

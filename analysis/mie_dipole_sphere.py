#!/usr/bin/env python3
"""
اعتبارسنجی تحلیلی حالت D (کره‌ی طلای هم‌حجم، دوقطبی شعاعی) با نظریه‌ی می
------------------------------------------------------------------------
نرخ واپاشی کل و تابشی یک دوقطبی شعاعی در فاصله‌ی r از مرکز کره‌ی فلزی
(Ruppin, J. Chem. Phys. 76, 1681 (1982); Kim, Leung & George, Surf. Sci. 195, 1 (1988);
Mertens, Koenderink & Polman, PRB 76, 115123 (2007)):

  Γ_tot/Γ0 = 1 + (3/2) Re Σ_n n(n+1)(2n+1) B_n [h_n(x)/x]^2
  Γ_rad/Γ0 = (3/(2x^2)) Σ_n n(n+1)(2n+1) |j_n(x) + B_n h_n(x)|^2 ,   x = k r

B_n = -a_n  (a_n ضریب می بوهرن–هافمن؛ در حد شبه‌استاتیک B_1 = i(2/3)(ka)^3 (ε-1)/(ε+2)).
داده‌ی طلا: جدول Johnson & Christy (1972) با درون‌یابی خطی در انرژی.

خروجی: analysis/D_sphere_mie_vs_fdtd.png  و  analysis/D_sphere_mie_vs_fdtd.txt
اجرا:   python3 analysis/mie_dipole_sphere.py
"""
import os, sys
import numpy as np
from scipy.special import spherical_jn, spherical_yn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'New folder (2)')

# --- Johnson & Christy (1972) gold, Table I: E(eV), n, k -------------------
JC = np.array([
 [0.64,0.92,13.78],[0.77,0.56,11.21],[0.89,0.43,9.519],[1.02,0.35,8.145],
 [1.14,0.27,7.150],[1.26,0.22,6.350],[1.39,0.17,5.663],[1.51,0.16,5.083],
 [1.64,0.14,4.542],[1.76,0.13,4.103],[1.88,0.14,3.697],[2.01,0.21,3.272],
 [2.13,0.29,2.863],[2.26,0.43,2.455],[2.38,0.62,2.081],[2.50,1.04,1.833],
 [2.63,1.31,1.849],[2.75,1.38,1.914],[2.88,1.45,1.948],[3.00,1.46,1.958],
])
def eps_au(lam_nm):
    E = 1239.84193/np.asarray(lam_nm, float)
    n = np.interp(E, JC[:,0], JC[:,1]); k = np.interp(E, JC[:,0], JC[:,2])
    return (n+1j*k)**2

def h1(n, z):  return spherical_jn(n, z) + 1j*spherical_yn(n, z)
def psi(n,z):  return z*spherical_jn(n,z)
def dpsi(n,z): return spherical_jn(n,z) + z*spherical_jn(n,z,derivative=True)
def xi(n,z):   return z*h1(n,z)
def dxi(n,z):  return h1(n,z) + z*(spherical_jn(n,z,derivative=True)+1j*spherical_yn(n,z,derivative=True))

def mie_an(n, xa, m):
    """ضریب a_n بوهرن–هافمن (TM) برای کره با پارامتر اندازه xa و ضریب شکست نسبی m."""
    mx = m*xa
    return (m*psi(n,mx)*dpsi(n,xa) - psi(n,xa)*dpsi(n,mx)) / \
           (m*psi(n,mx)*dxi(n,xa)  - xi(n,xa)*dpsi(n,mx))

def rates_radial(lam_nm, a_nm, r_nm, nmax=60):
    k  = 2*np.pi/lam_nm
    xa = k*a_nm; x = k*r_nm
    m  = np.sqrt(eps_au(lam_nm))
    tot = 0j; rad = 0.0
    for n in range(1, nmax+1):
        Bn = -mie_an(n, xa, m)
        w  = n*(n+1)*(2*n+1)
        tot += w*Bn*(h1(n,x)/x)**2
        rad += w*abs(spherical_jn(n,x) + Bn*h1(n,x))**2
    return 1 + 1.5*tot.real, 1.5*rad/x**2

def load(tag):
    rows=[l.split() for l in open(os.path.join(DATA, tag+'_spectra.txt')).read().splitlines()[1:] if l.strip()]
    return np.array(rows, float)

if __name__ == '__main__':
    a, gap = 15.874, 5.0
    D = load('D_sphere_R15.9'); B = load('B_freespace')
    lam = D[:,0]
    Fp_m = np.array([rates_radial(L, a, a+gap)[0] for L in lam])
    T_m  = np.array([rates_radial(L, a, a+gap)[1] for L in lam])
    Fp_f, T_f = D[:,1], D[:,2]
    Fp_c, T_c = D[:,1]/B[:,1], D[:,2]/B[:,2]

    iM = Fp_m.argmax(); iF = Fp_f.argmax(); jM = T_m.argmax(); jF = T_f.argmax()
    lines = [
      'Analytical (Mie, radial dipole, a=%.3f nm, gap=%.1f nm, JC gold) vs FDTD case D' % (a,gap),
      'Fp_max  Mie = %.1f @ %.0f nm | FDTD raw = %.1f @ %.0f nm | FDTD/B-corrected = %.1f @ %.0f nm'
        % (Fp_m[iM], lam[iM], Fp_f[iF], lam[iF], Fp_c.max(), lam[Fp_c.argmax()]),
      'T_max   Mie = %.2f @ %.0f nm | FDTD raw = %.2f @ %.0f nm | corrected = %.2f @ %.0f nm'
        % (T_m[jM], lam[jM], T_f[jF], lam[jF], T_c.max(), lam[T_c.argmax()]),
      'eta at Fp-peak: Mie %.2f %% | FDTD %.2f %%' % (100*T_m[iM]/Fp_m[iM], 100*T_f[iF]/Fp_f[iF]),
      'ratio FDTD/Mie of Fp at 508, 532, 610 nm: ' + ', '.join('%.2f' % (Fp_f[lam==L][0]/Fp_m[lam==L][0]) for L in (508,532,610)),
      'ratio FDTD/Mie of T  at 508, 532, 610 nm: ' + ', '.join('%.2f' % (T_f[lam==L][0]/T_m[lam==L][0]) for L in (508,532,610)),
      '', 'lambda_nm\tFp_mie\tT_mie\tFp_fdtd\tT_fdtd']
    lines += ['%.0f\t%.3f\t%.4f\t%.3f\t%.4f' % t for t in zip(lam,Fp_m,T_m,Fp_f,T_f)]
    out = os.path.join(ROOT,'analysis','D_sphere_mie_vs_fdtd.txt')
    open(out,'w').write('\n'.join(lines)); print('\n'.join(lines[:6]))

    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2,1, figsize=(6.4,6.6), sharex=True)
    ax[0].plot(lam, Fp_f, label='FDTD (raw)'); ax[0].plot(lam, Fp_c, '--', label='FDTD / $F_{p,B}$')
    ax[0].plot(lam, Fp_m, 'k:', lw=2, label='Mie theory (analytical)')
    ax[0].set_ylabel('$F_p$'); ax[0].legend(); ax[0].grid(alpha=.3)
    ax[1].plot(lam, T_f, label='FDTD (raw)'); ax[1].plot(lam, T_c, '--', label='FDTD / $T_B$')
    ax[1].plot(lam, T_m, 'k:', lw=2, label='Mie theory (analytical)')
    ax[1].set_ylabel('$T=P_{rad}/P_0$'); ax[1].set_xlabel('Wavelength (nm)'); ax[1].legend(); ax[1].grid(alpha=.3)
    fig.suptitle('Case D: gold sphere R=%.3f nm, radial dipole, gap %.0f nm' % (a,gap))
    fig.tight_layout(); fig.savefig(os.path.join(ROOT,'analysis','D_sphere_mie_vs_fdtd.png'), dpi=160)
    fig.savefig(os.path.join(ROOT,'manuscript','figures','D_sphere_mie_vs_fdtd.pdf'))
    fig.savefig(os.path.join(ROOT,'manuscript','figures','web','D_sphere_mie_vs_fdtd.png'), dpi=150)
    print('saved figure')

    # --- پویش گاف تحلیلی (جایگزین موقت حالت‌های F_gap3/10/20 که اجرا نشده‌اند) ---
    gaps=[3,5,10,15,20,30]; lam2=np.arange(500,901,2.0); rows=[]
    fig,ax=plt.subplots(1,3,figsize=(10,3.2))
    for gp in gaps:
        F=np.array([rates_radial(L,a,a+gp)[0] for L in lam2]); Tt=np.array([rates_radial(L,a,a+gp)[1] for L in lam2])
        ax[0].semilogy(lam2,F,label='gap %g nm'%gp); ax[1].plot(lam2,Tt); ax[2].semilogy(lam2,100*Tt/F)
        i=F.argmax(); j=Tt.argmax(); rows.append((gp,lam2[i],F[i],lam2[j],Tt[j],100*Tt[i]/F[i],100*(Tt/F).max()))
    ax[0].set_ylabel('$F_p$'); ax[1].set_ylabel('$T$'); ax[2].set_ylabel('$\\eta_a$ (%)')
    for A_ in ax: A_.set_xlabel('Wavelength (nm)'); A_.grid(alpha=.3)
    ax[0].legend(fontsize=7); fig.suptitle('Mie theory: radial dipole near Au sphere R=%.3f nm, gap sweep'%a); fig.tight_layout()
    fig.savefig(os.path.join(ROOT,'manuscript','figures','fig_gap_sweep_mie.pdf')); fig.savefig(os.path.join(ROOT,'manuscript','figures','web','fig_gap_sweep_mie.png'),dpi=150)
    hdr='gap_nm\tlam_Fp\tFp_max\tlam_T\tT_max\teta_at_Fp_peak_%\teta_max_%'
    txt='\n'.join([hdr]+['%g\t%.0f\t%.1f\t%.0f\t%.2f\t%.2f\t%.1f'%r for r in rows])
    open(os.path.join(ROOT,'analysis','gap_sweep_mie.txt'),'w').write(txt); print(txt)

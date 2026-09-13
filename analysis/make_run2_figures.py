#!/usr/bin/env python3
"""شکل‌های مقاله از داده‌ی خام اجرای دوم و سوم — اجرا: python3 analysis/make_run2_figures.py

داده: New folder (2)/  (B, C, D)   و   New folder3/  (A, G_mesh3, G_mesh1.5, D_tan, F_gap3/10/20)
خروجی در manuscript/figures/ (+ PNG در figures/web/):
  fig_spectra_all      طیف F_p و T حالت‌های A, B, C, D (لگاریتمی)
  fig_efficiency       بازده تابشی A, C, D
  fig_freespace_B      مرجع فضای آزاد
  fig_nearfield        میدان نزدیک A, C, D با مقیاس مشترک و ماسک منبع
  fig_mesh             همگرایی مش (۳، ۲، ۱٫۵ nm) برای حالت A
  fig_gap              پویش گاف (۳، ۵، ۱۰، ۲۰ nm) نانومیله
  fig_anisotropy       ناهمسانگردی جهتی: میله (طولی/عرضی) در برابر کره (شعاعی/مماسی)
و جدول متنی analysis/summary_all_cases.txt
"""
import os, glob, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS=[os.path.join(ROOT,'New folder (2)'), os.path.join(ROOT,'New folder3')]
FIG=os.path.join(ROOT,'manuscript','figures'); WEB=os.path.join(FIG,'web'); os.makedirs(WEB,exist_ok=True)

def find(name):
    for d in DIRS:
        p=os.path.join(d,name)
        if os.path.isfile(p): return p
    return None
def load(tag):
    p=find(tag+'_spectra.txt')
    if p is None: return None
    return np.array([l.split() for l in open(p).read().splitlines()[1:] if l.strip()],float)
def nf(tag):
    p=find(tag+'_nearfield.txt')
    if p is None: return None
    L=open(p).read().splitlines(); z=np.array(L[0].split()[1:],float)
    M=np.array([l.split() for l in L[1:] if l.strip()],float); return M[:,0],z,M[:,1:]
def save(fig,name):
    fig.savefig(os.path.join(FIG,name+'.pdf')); fig.savefig(os.path.join(WEB,name+'.png'),dpi=150); plt.close(fig)

S={k:load(k) for k in ['A_baseline','B_freespace','C_tip_transverse','D_sphere_R15.9','D_sphere_R15.9_tan',
                       'G_mesh3','G_mesh1.5','F_gap3','F_gap10','F_gap20']}
A,B,C,D=S['A_baseline'],S['B_freespace'],S['C_tip_transverse'],S['D_sphere_R15.9']
lam=B[:,0]
if A is None: raise SystemExit('A_baseline_spectra.txt پیدا نشد — New folder3 را چک کن')

# ---------------- جدول خلاصه ----------------
rows=['case\tlam_Fp\tFp_max\tlam_T\tT_max\teta_at_Fp_peak_%\teta_at_T_peak_%\teta_max_%\tlam_eta_max']
for k,X in S.items():
    if X is None: continue
    i=X[:,1].argmax(); j=X[:,2].argmax(); e=X[:,3].argmax()
    rows.append('%s\t%d\t%.1f\t%d\t%.2f\t%.2f\t%.2f\t%.1f\t%d'%(k,lam[i],X[i,1],lam[j],X[j,2],100*X[i,3],100*X[j,3],100*X[e,3],lam[e]))
open(os.path.join(ROOT,'analysis','summary_all_cases.txt'),'w').write('\n'.join(rows)); print('\n'.join(rows))

# ---------------- شکل: طیف همه‌ی حالت‌ها ----------------
fig,ax=plt.subplots(2,1,figsize=(6.4,7),sharex=True)
for X,lab,st in [(A,'A: rod, longitudinal dipole','r-'),(C,'C: rod, transverse dipole','b-'),(D,'D: equal-volume sphere, radial','-'),(B,'B: free space','k--')]:
    ax[0].semilogy(lam,X[:,1],st,lw=1.6 if st=='r-' else 1.2,label=lab, color=None if st!='-' else 'tab:orange')
    ax[1].semilogy(lam,X[:,2],st,lw=1.6 if st=='r-' else 1.2, color=None if st!='-' else 'tab:orange')
ax[0].set_ylabel('$F_p = P_{tot}/P_0$'); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3,which='both')
ax[1].set_ylabel('$T = P_{rad}/P_0$'); ax[1].set_xlabel('Wavelength (nm)'); ax[1].grid(alpha=.3,which='both')
fig.tight_layout(); save(fig,'fig_spectra_all')

# ---------------- شکل: بازده ----------------
fig,ax=plt.subplots(figsize=(6.4,3.6))
ax.semilogy(lam,100*A[:,3],'r',label='A: rod, longitudinal'); ax.semilogy(lam,100*C[:,3],'b',label='C: rod, transverse'); ax.semilogy(lam,100*D[:,3],color='tab:orange',label='D: sphere, radial')
ax.axvline(610,color='r',ls=':',lw=.8); ax.set_ylabel('$\\eta_a = T/F_p$ (%)'); ax.set_xlabel('Wavelength (nm)'); ax.legend(fontsize=8); ax.grid(alpha=.3,which='both')
fig.tight_layout(); save(fig,'fig_efficiency')

# ---------------- شکل: مرجع فضای آزاد ----------------
fig,ax=plt.subplots(figsize=(6.4,3.6))
ax.plot(lam,B[:,1],label='$F_{p,B}$'); ax.plot(lam,B[:,2],label='$T_B$'); ax.plot(lam,B[:,3],label='$\\eta_B=T_B/F_{p,B}$')
ax.axhline(1,color='k',ls='--',lw=1); ax.set_xlabel('Wavelength (nm)'); ax.set_ylabel('free-space check'); ax.legend(); ax.grid(alpha=.3)
fig.tight_layout(); save(fig,'fig_freespace_B')

# ---------------- شکل: میدان نزدیک A, C, D ----------------
pan=[('A_baseline','A: rod, longitudinal, 610 nm',(0,35),'rod'),('C_tip_transverse','C: rod, transverse, 610 nm',(0,35),'rod'),('D_sphere_R15.9','D: sphere, radial, 530 nm',(0,21.02),'sph')]
pan=[p for p in pan if nf(p[0]) is not None]
fig,ax=plt.subplots(1,len(pan),figsize=(3.6*len(pan)+1,3.8)); ax=np.atleast_1d(ax)
vmin,vmax=1e2,1e9
for a,(tag,title,src,g) in zip(ax,pan):
    x,z,E=nf(tag); E=E.copy(); X,Z=np.meshgrid(x,z,indexing='ij')
    E[(X-src[0])**2+(Z-src[1])**2<3.0**2]=np.nan
    im=a.pcolormesh(x,z,E.T,norm=LogNorm(vmin,vmax),cmap='inferno',shading='nearest')
    if g=='rod':
        th=np.linspace(0,np.pi,50); a.plot([-10,-10],[-20,20],'w',lw=1); a.plot([10,10],[-20,20],'w',lw=1)
        a.plot(10*np.cos(th),20+10*np.sin(th),'w',lw=1); a.plot(10*np.cos(th),-20-10*np.sin(th),'w',lw=1)
    else:
        th=np.linspace(0,2*np.pi,100); a.plot(15.874*np.cos(th),15.874*np.sin(th),'w',lw=1)
    a.plot(*src,'c*',ms=8); a.set_title(title,fontsize=9); a.set_xlabel('x (nm)'); a.set_aspect('equal'); a.set_xlim(-60,60); a.set_ylim(-60,60)
ax[0].set_ylabel('z (nm)'); cb=fig.colorbar(im,ax=ax,shrink=.85); cb.set_label('$|E|^2$ (Lumerical units, common scale)')
save(fig,'fig_nearfield')

# ---------------- شکل: همگرایی مش ----------------
fig,ax=plt.subplots(1,3,figsize=(10.5,3.3))
for k,lab,c in [('G_mesh3','$\\Delta=3$ nm','tab:green'),('A_baseline','$\\Delta=2$ nm (main)','r'),('G_mesh1.5','$\\Delta=1.5$ nm','tab:purple')]:
    X=S[k]
    if X is None: continue
    ax[0].plot(lam,X[:,1],color=c,label=lab); ax[1].plot(lam,X[:,2],color=c,label=lab); ax[2].plot(lam,100*X[:,3],color=c,label=lab)
ax[0].set_ylabel('$F_p$'); ax[1].set_ylabel('$T$'); ax[2].set_ylabel('$\\eta_a$ (%)')
for a in ax: a.set_xlabel('Wavelength (nm)'); a.grid(alpha=.3)
ax[0].legend(fontsize=8); fig.suptitle('Mesh study: rod, longitudinal dipole, gap 5 nm',fontsize=10); fig.tight_layout(); save(fig,'fig_mesh')

# ---------------- شکل: پویش گاف ----------------
fig,ax=plt.subplots(1,3,figsize=(10.5,3.3))
for k,lab in [('F_gap3','gap 3 nm (mesh 1 nm)'),('A_baseline','gap 5 nm'),('F_gap10','gap 10 nm'),('F_gap20','gap 20 nm')]:
    X=S[k]
    if X is None: continue
    ax[0].semilogy(lam,X[:,1],label=lab); ax[1].semilogy(lam,X[:,2],label=lab); ax[2].semilogy(lam,100*X[:,3],label=lab)
ax[0].set_ylabel('$F_p$'); ax[1].set_ylabel('$T$'); ax[2].set_ylabel('$\\eta_a$ (%)')
for a in ax: a.set_xlabel('Wavelength (nm)'); a.grid(alpha=.3,which='both')
ax[0].legend(fontsize=8); fig.suptitle('Gap sweep: rod, longitudinal dipole',fontsize=10); fig.tight_layout(); save(fig,'fig_gap')

# ---------------- شکل: ناهمسانگردی جهتی میله در برابر کره ----------------
Dt=S['D_sphere_R15.9_tan']
fig,ax=plt.subplots(1,2,figsize=(8,3.4))
ax[0].semilogy(lam,A[:,1]/C[:,1],'r',label='rod: longitudinal / transverse')
ax[1].semilogy(lam,A[:,2]/C[:,2],'r',label='rod: longitudinal / transverse')
if Dt is not None:
    ax[0].semilogy(lam,D[:,1]/Dt[:,1],color='tab:orange',label='sphere: radial / tangential')
    ax[1].semilogy(lam,D[:,2]/Dt[:,2],color='tab:orange',label='sphere: radial / tangential')
ax[0].set_ylabel('$F_p$ ratio'); ax[1].set_ylabel('$T$ ratio')
for a in ax: a.set_xlabel('Wavelength (nm)'); a.grid(alpha=.3,which='both'); a.axhline(1,color='k',lw=.8,ls='--')
ax[0].legend(fontsize=8); fig.suptitle('Orientation anisotropy at fixed gap 5 nm',fontsize=10); fig.tight_layout(); save(fig,'fig_anisotropy')
print('done')

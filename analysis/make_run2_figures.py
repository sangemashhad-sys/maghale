#!/usr/bin/env python3
"""شکل‌های مقاله از داده‌ی خام اجرای دوم (New folder (2)) — اجرا: python3 analysis/make_run2_figures.py
خروجی در manuscript/figures/ : fig_spectra_all.pdf/.png , fig_freespace_B.pdf/.png , fig_nearfield_CD.pdf/.png
حالت A فایل خام ندارد؛ فقط قله‌ی گزارش‌شده و منحنی رقم‌زنی‌شده (اگر _probe موجود باشد) رسم می‌شود."""
import os, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(ROOT,'New folder (2)')
FIG=os.path.join(ROOT,'manuscript','figures'); WEB=os.path.join(FIG,'web'); os.makedirs(WEB,exist_ok=True)
def load(tag): return np.array([l.split() for l in open(os.path.join(DATA,tag+'_spectra.txt')).read().splitlines()[1:] if l.strip()],float)
B=load('B_freespace'); C=load('C_tip_transverse'); D=load('D_sphere_R15.9'); lam=B[:,0]
A_FP=(610,1490.0); A_T=(616,119.219)
def save(fig,name):
    fig.savefig(os.path.join(FIG,name+'.pdf')); fig.savefig(os.path.join(WEB,name+'.png'),dpi=150); plt.close(fig)

# --- شکل ۱: طیف‌های F_p و T هر سه حالت (لگاریتمی) -------------------------
fig,ax=plt.subplots(2,1,figsize=(6.4,7),sharex=True)
ax[0].semilogy(lam,C[:,1],label='C: rod, transverse dipole'); ax[0].semilogy(lam,D[:,1],label='D: equal-volume sphere')
ax[0].semilogy(lam,B[:,1],'k--',lw=1,label='B: free space'); ax[0].plot(*A_FP,'r*',ms=12,label='A: rod, longitudinal (reported peak)')
ax[0].set_ylabel('$F_p = P_{tot}/P_0$'); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3,which='both')
ax[1].semilogy(lam,C[:,2],label='C'); ax[1].semilogy(lam,D[:,2],label='D'); ax[1].semilogy(lam,B[:,2],'k--',lw=1,label='B')
ax[1].plot(*A_T,'r*',ms=12,label='A (reported peak)'); ax[1].set_ylabel('$T = P_{rad}/P_0$'); ax[1].set_xlabel('Wavelength (nm)')
ax[1].legend(fontsize=8); ax[1].grid(alpha=.3,which='both'); fig.tight_layout(); save(fig,'fig_spectra_all')

# --- شکل ۲: بازده تابشی -----------------------------------------------------
fig,ax=plt.subplots(figsize=(6.4,3.6))
ax.semilogy(lam,100*C[:,3],label='C: rod, transverse'); ax.semilogy(lam,100*D[:,3],label='D: sphere')
ax.axhline(8.0,color='r',ls=':',label='A: upper bound at $\\lambda_{F_p}$ (8.0 %)')
ax.set_ylabel('$\\eta_a = T/F_p$ (%)'); ax.set_xlabel('Wavelength (nm)'); ax.legend(fontsize=8); ax.grid(alpha=.3,which='both')
fig.tight_layout(); save(fig,'fig_efficiency')

# --- شکل ۳: مرجع فضای آزاد ---------------------------------------------------
fig,ax=plt.subplots(figsize=(6.4,3.6))
ax.plot(lam,B[:,1],label='$F_{p,B}$'); ax.plot(lam,B[:,2],label='$T_B$'); ax.plot(lam,B[:,3],label='$\\eta_B=T_B/F_{p,B}$')
ax.axhline(1,color='k',ls='--',lw=1); ax.set_xlabel('Wavelength (nm)'); ax.set_ylabel('free-space check'); ax.legend(); ax.grid(alpha=.3)
fig.tight_layout(); save(fig,'fig_freespace_B')

# --- شکل ۴: میدان نزدیک با مقیاس مشترک و ماسک منبع -------------------------
def nf(tag):
    L=open(os.path.join(DATA,tag+'_nearfield.txt')).read().splitlines(); z=np.array(L[0].split()[1:],float)
    M=np.array([l.split() for l in L[1:] if l.strip()],float); return M[:,0],z,M[:,1:]
fig,ax=plt.subplots(1,2,figsize=(8,3.8))
pan=[('C_tip_transverse','C: rod, transverse dipole, 610 nm',(0,35)),('D_sphere_R15.9','D: sphere, 530 nm',(0,21.02))]
vmin,vmax=1e2,1e9
for a,(tag,title,src) in zip(ax,pan):
    x,z,E=nf(tag); E=E.copy(); X,Z=np.meshgrid(x,z,indexing='ij')
    E[(X-src[0])**2+(Z-src[1])**2<3.0**2]=np.nan  # ماسک ۳ نانومتری حول تکینگی منبع
    im=a.pcolormesh(x,z,E.T,norm=LogNorm(vmin,vmax),cmap='inferno',shading='nearest')
    if tag.startswith('C'):
        th=np.linspace(0,np.pi,50); a.plot([-10,-10],[-20,20],'w',lw=1); a.plot([10,10],[-20,20],'w',lw=1)
        a.plot(10*np.cos(th),20+10*np.sin(th),'w',lw=1); a.plot(10*np.cos(th),-20-10*np.sin(th),'w',lw=1)
    else:
        th=np.linspace(0,2*np.pi,100); a.plot(15.874*np.cos(th),15.874*np.sin(th),'w',lw=1)
    a.plot(*src,'c*',ms=8); a.set_title(title,fontsize=9); a.set_xlabel('x (nm)'); a.set_aspect('equal'); a.set_xlim(-60,60); a.set_ylim(-60,60)
ax[0].set_ylabel('z (nm)'); cb=fig.colorbar(im,ax=ax,shrink=.85); cb.set_label('$|E|^2$ (Lumerical units, common scale)')
save(fig,'fig_nearfield_CD')
print('done')

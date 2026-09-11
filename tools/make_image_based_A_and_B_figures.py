#!/usr/bin/env python3
"""Publication figures for second-test A screenshot and exact B data.

A points are manually digitized from the Lumerical plot supplied by the user;
no claim is made that they are the unavailable raw monitor export. B is read
from the exact 201-point text export.
"""
from pathlib import Path
import csv
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/test2'; FIG=ROOT/'manuscript/figures'; WEB=FIG/'web'
for p in (OUT,FIG,WEB): p.mkdir(parents=True,exist_ok=True)

# Approximate readings from the supplied 500--900 nm Lumerical screenshot.
# Dense anchors are used around the narrow longitudinal resonance.
L=np.array([500,505,510,515,520,530,540,550,560,570,580,588,594,600,604,
            608,610,612,616,620,625,630,640,650,660,670,680,690,700,710,
            720,730,740,750,760,770,780,790,800,810,820,830,840,850,860,
            870,880,890,900],float)
F=np.array([600,625,640,642,625,570,510,465,450,475,600,800,1020,1260,1420,
            1485,1490,1470,1320,1120,850,650,445,350,280,225,180,150,130,112,
            95,88,78,74,72,65,61,63,64,60,56,55,58,59,56,52,50,53,55],float)
ld=np.linspace(500,900,801); fd=PchipInterpolator(L,F)(ld)
with (OUT/'A_purcell_digitized_from_image.csv').open('w',newline='') as f:
    w=csv.writer(f); w.writerow(['lambda_nm','Fp_digitized_approx']); w.writerows(zip(ld,fd))

plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.35})
fig,ax=plt.subplots(figsize=(7.2,4.7),constrained_layout=True)
ax.plot(ld,fd,color='#58aaf4',lw=2.2)
ax.scatter([610],[1490],s=28,color='#1f6fb2',zorder=3)
ax.annotate(r'$F_p\approx1490$ at $\lambda\approx610$ nm',xy=(610,1490),xytext=(660,1370),
            arrowprops={'arrowstyle':'->','color':'#555'},fontsize=9)
ax.set(xlim=(500,900),ylim=(0,1600),xlabel='Wavelength (nm)',ylabel=r'Purcell factor $F_p$')
for ext in ('pdf','png'):
    path=(FIG/'Test2_A_Purcell_full.pdf') if ext=='pdf' else (WEB/'Test2_A_Purcell_full.png')
    fig.savefig(path,dpi=220 if ext=='png' else None,bbox_inches='tight')
plt.close(fig)

b=np.genfromtxt(ROOT/'New folder (2)/B_freespace_spectra.txt',names=True,delimiter='\t')
fig,ax=plt.subplots(figsize=(7.2,4.5),constrained_layout=True)
ax.plot(b['lambda_nm'],b['Fp'],color='#58aaf4',lw=2.2,label=r'$F_{p,B}$')
ax.axhline(1,color='#444',lw=1,ls='--',label='Ideal free-space value')
ax.set(xlim=(500,900),ylim=(.92,1.14),xlabel='Wavelength (nm)',ylabel=r'Free-space $F_{p,B}$')
ax.legend(fontsize=9)
for ext in ('pdf','png'):
    path=(FIG/'Test2_B_Freespace.pdf') if ext=='pdf' else (WEB/'Test2_B_Freespace.png')
    fig.savefig(path,dpi=220 if ext=='png' else None,bbox_inches='tight')
plt.close(fig)

# Preserve the already generated exact C/D comparison as a manuscript figure.
for ext in ('pdf','png'):
    src=OUT/f'spectra_comparison.{ext}'
    dst=(FIG/'Test2_CD_Controls.pdf') if ext=='pdf' else (WEB/'Test2_CD_Controls.png')
    dst.write_bytes(src.read_bytes())
print('Wrote digitized A, exact B, and exact C/D figures.')

#!/usr/bin/env python3
"""Build honest manuscript figures from the available second-test data.

A has only two user-reported peak points; it is therefore shown as a marker,
not as an invented continuous curve. C and D are baseline-corrected with B.
"""
from pathlib import Path
import csv
import numpy as np
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'analysis/test2/spectra_normalized.csv'
FIG=ROOT/'manuscript/figures'; WEB=FIG/'web'
FIG.mkdir(parents=True,exist_ok=True); WEB.mkdir(parents=True,exist_ok=True)
rows=list(csv.DictReader(SRC.open()))
def col(name): return np.array([float(r[name]) for r in rows])
lam=col('lambda_nm')
plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.25,'figure.dpi':150})

def save(name):
    plt.savefig(FIG/f'{name}.pdf',bbox_inches='tight')
    plt.savefig(WEB/f'{name}.png',dpi=220,bbox_inches='tight')
    plt.close()

plt.figure(figsize=(7.2,4.6))
plt.semilogy(lam,col('C_Fp'),lw=2,label='Rod, transverse dipole (C)')
plt.semilogy(lam,col('D_Fp'),lw=2,label='Equal-volume sphere (D)')
plt.scatter([610],[1490],s=80,marker='*',color='#b2182b',zorder=5,
            label=r'Rod, longitudinal dipole (A): $F_p\approx1490$')
plt.annotate('reported peak\n~610 nm',xy=(610,1490),xytext=(655,850),
             arrowprops={'arrowstyle':'->','color':'#555'},ha='left')
plt.xlabel('Wavelength (nm)'); plt.ylabel(r'Purcell factor $F_p$')
plt.xlim(495,905); plt.ylim(.8,2500); plt.legend(loc='best',fontsize=9)
plt.tight_layout(); save('Test2_Purcell')

plt.figure(figsize=(7.2,4.6))
plt.semilogy(lam,col('C_T'),lw=2,label='Rod, transverse dipole (C)')
plt.semilogy(lam,col('D_T'),lw=2,label='Equal-volume sphere (D)')
plt.scatter([616],[119.219],s=80,marker='*',color='#b2182b',zorder=5,
            label=r'Rod, longitudinal dipole (A): $T_{max}=119.219$')
plt.annotate('reported peak\n616 nm',xy=(616,119.219),xytext=(670,60),
             arrowprops={'arrowstyle':'->','color':'#555'},ha='left')
plt.xlabel('Wavelength (nm)'); plt.ylabel(r'Radiated-power enhancement $T$')
plt.xlim(495,905); plt.ylim(.1,200); plt.legend(loc='best',fontsize=9)
plt.tight_layout(); save('Test2_Radiated')

# The exact C/D near-field map is produced by analyze_test2.py.
for ext in ('pdf','png'):
    src=ROOT/f'analysis/test2/nearfield_log_comparison.{ext}'
    dst=(FIG/'Test2_Nearfield_controls.pdf') if ext=='pdf' else (WEB/'Test2_Nearfield_controls.png')
    dst.write_bytes(src.read_bytes())
print('Wrote test-two manuscript figures.')

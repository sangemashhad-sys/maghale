#!/usr/bin/env python3
"""Analyze the second Lumerical validation run (B/C/D datasets).

Inputs: New folder (2)/*_spectra.txt and *_nearfield.txt
Outputs: analysis/test2/ (CSVs, figures, machine-readable and Persian reports)
"""
from pathlib import Path
import csv, json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Rectangle, Circle

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "New folder (2)"
OUT = ROOT / "analysis" / "test2"
OUT.mkdir(parents=True, exist_ok=True)

CASES = {
    "B": ("B_freespace", "Free space"),
    "C": ("C_tip_transverse", "Rod, transverse dipole"),
    "D": ("D_sphere_R15.9", "Equal-volume sphere"),
}

def spectrum(stem):
    a = np.genfromtxt(SRC / f"{stem}_spectra.txt", names=True, delimiter="\t")
    return {n: np.asarray(a[n], float) for n in a.dtype.names}

def field(stem):
    rows = list(csv.reader((SRC / f"{stem}_nearfield.txt").open(), delimiter="\t"))
    # The exported matrix labels its header as x_nm, but source-location checks
    # prove that columns are z and rows are x (C peaks at x=0,z=35 nm; D at
    # x=0,z=20.874 nm). Return conventional x,z and transpose to (z,x).
    z = np.asarray([float(v) for v in rows[0][1:]])
    x = np.asarray([float(r[0]) for r in rows[1:]])
    val_xz = np.asarray([[float(v) for v in r[1:]] for r in rows[1:]])
    return x, z, val_xz.T

def peak(lam, y):
    i = int(np.nanargmax(y))
    return i, float(lam[i]), float(y[i])

S = {k: spectrum(v[0]) for k,v in CASES.items()}
lam = S["B"]["lambda_nm"]
assert all(np.array_equal(lam, s["lambda_nm"]) for s in S.values())

# The free-space run captures wavelength-dependent numerical baseline error.
for key in ("C", "D"):
    S[key]["Fp_over_B"] = S[key]["Fp"] / S["B"]["Fp"]
    S[key]["T_over_B"] = S[key]["T"] / S["B"]["T"]
    S[key]["eta_corrected"] = S[key]["T_over_B"] / S[key]["Fp_over_B"]

summary = {"source_directory": str(SRC.relative_to(ROOT)), "samples": int(len(lam)),
           "lambda_nm": [float(lam.min()), float(lam.max())], "cases": {}}
for key,(stem,label) in CASES.items():
    s=S[key]
    iF,lF,F=peak(lam,s["Fp"]); iT,lT,T=peak(lam,s["T"])
    d={"stem":stem,"label":label,"Fp_raw_peak":{"lambda_nm":lF,"value":F},
       "T_raw_peak":{"lambda_nm":lT,"value":T},
       "T_at_Fp_raw_peak":float(s["T"][iF]),
       "eta_at_Fp_raw_peak":float(s["T"][iF]/s["Fp"][iF])}
    if key in ("C","D"):
        iFc,lFc,Fc=peak(lam,s["Fp_over_B"]); iTc,lTc,Tc=peak(lam,s["T_over_B"])
        d.update({"Fp_baseline_corrected_peak":{"lambda_nm":lFc,"value":Fc},
                  "T_baseline_corrected_peak":{"lambda_nm":lTc,"value":Tc},
                  "T_corrected_at_Fp_corrected_peak":float(s["T_over_B"][iFc]),
                  "eta_corrected_at_Fp_corrected_peak":float(s["eta_corrected"][iFc])})
    summary["cases"][key]=d

# Near-field maxima and source coordinates implied by builder script.
field_specs={"C": {"stem":"C_tip_transverse","source_nm":[0.0,35.0],"geometry":"rod","lambda_nm":610.0},
             "D": {"stem":"D_sphere_R15.9","source_nm":[0.0,20.874],"geometry":"sphere","lambda_nm":530.0}}
for key,spec in field_specs.items():
    x,z,a=field(spec["stem"])
    iz,ix=np.unravel_index(np.nanargmax(a),a.shape)
    summary["cases"][key]["nearfield"]={"shape":[int(a.shape[0]),int(a.shape[1])],
        "max_value":float(a[iz,ix]),"max_position_nm":[float(x[ix]),float(z[iz])],
        "source_position_nm":spec["source_nm"],"monitor_lambda_nm":spec["lambda_nm"]}

(OUT/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

# Combined numerical table.
with (OUT/"spectra_normalized.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["lambda_nm","B_Fp","B_T","C_Fp","C_T","C_Fp_over_B",
        "C_T_over_B","C_eta_corrected","D_Fp","D_T","D_Fp_over_B","D_T_over_B","D_eta_corrected"])
    for i,L in enumerate(lam):
        w.writerow([L,S['B']['Fp'][i],S['B']['T'][i],S['C']['Fp'][i],S['C']['T'][i],
          S['C']['Fp_over_B'][i],S['C']['T_over_B'][i],S['C']['eta_corrected'][i],
          S['D']['Fp'][i],S['D']['T'][i],S['D']['Fp_over_B'][i],S['D']['T_over_B'][i],S['D']['eta_corrected'][i]])

plt.rcParams.update({"font.size":10,"axes.grid":True,"grid.alpha":.25})
fig,ax=plt.subplots(2,1,figsize=(7.2,7),sharex=True,constrained_layout=True)
for key,color in [("C","#2474b7"),("D","#d55e00")]:
    ax[0].plot(lam,S[key]["Fp_over_B"],label=CASES[key][1],color=color,lw=2)
    ax[1].plot(lam,S[key]["T_over_B"],label=CASES[key][1],color=color,lw=2)
ax[0].set_ylabel(r"$F_p/F_{p,\mathrm{free}}$"); ax[1].set_ylabel(r"$T/T_{\mathrm{free}}$")
ax[1].set_xlabel("Wavelength (nm)"); ax[0].legend(); ax[1].legend()
fig.savefig(OUT/"spectra_comparison.pdf"); fig.savefig(OUT/"spectra_comparison.png",dpi=220); plt.close(fig)

fig,ax=plt.subplots(figsize=(7.2,4.2),constrained_layout=True)
for key,color in [("C","#2474b7"),("D","#d55e00")]:
    ax.plot(lam,100*S[key]["eta_corrected"],label=CASES[key][1],color=color,lw=2)
ax.set(xlabel="Wavelength (nm)",ylabel="Baseline-corrected radiation efficiency (%)")
ax.legend(); fig.savefig(OUT/"efficiency_comparison.pdf"); fig.savefig(OUT/"efficiency_comparison.png",dpi=220); plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(10,4.2),constrained_layout=True)
for ax,(key,spec) in zip(axs,field_specs.items()):
    x,z,a=field(spec["stem"]); positive=a[a>0]
    im=ax.pcolormesh(x,z,a,shading="auto",cmap="turbo",
                     norm=LogNorm(vmin=max(np.percentile(positive,2),positive.min()),vmax=positive.max()))
    if spec["geometry"]=="rod":
        ax.add_patch(Rectangle((-10,-20),20,40,fill=False,edgecolor="white",lw=1))
        ax.add_patch(Circle((0,20),10,fill=False,edgecolor="white",lw=1))
        ax.add_patch(Circle((0,-20),10,fill=False,edgecolor="white",lw=1))
    else: ax.add_patch(Circle((0,0),15.874,fill=False,edgecolor="white",lw=1))
    ax.plot(*spec["source_nm"],marker="*",ms=9,color="white",mec="black",label="Dipole")
    ax.set(title=f"{CASES[key][1]} — {spec['lambda_nm']:.0f} nm",
           xlabel="x (nm)",ylabel="z (nm)",aspect="equal")
    fig.colorbar(im,ax=ax,label=r"$|E|^2$ (simulation units)")
fig.savefig(OUT/"nearfield_log_comparison.pdf"); fig.savefig(OUT/"nearfield_log_comparison.png",dpi=220); plt.close(fig)
print(json.dumps(summary,indent=2))

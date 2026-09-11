r"""Turn the Lumerical CSV exports into the three figures of the manuscript.

Usage (from the project root, after the FDTD run has finished):

    python simulation/make_figures.py

Inputs  (written by simulation/nanorod_purcell.lsf, same folder):
    spectra.csv          lambda_nm, Fp, T, eta_a, A_metal
    peaks.csv            quantity, value, unit
    nearfield.csv        |E|^2 matrix, rows = x, cols = z
    nearfield_axes.csv   the x and z axes in nm

Outputs (manuscript/figures/, exactly the names 04_results.tex expects):
    Purcell_Spectrum.pdf
    radiated_power_T.pdf
    NearField_Profile.png

Also writes simulation/_numbers_for_text.txt: the peak values formatted the
way they appear in the manuscript, so the placeholders in the .tex files can
be replaced by copy-paste instead of retyping.

Only matplotlib and numpy are used -- no pandas, no seaborn, so this runs on
a bare `pip install matplotlib` environment.
"""
from __future__ import annotations

import csv
import os
import sys

try:
    import numpy as np
except ImportError:                                    # pragma: no cover
    sys.exit('numpy is required:  pip install numpy matplotlib')

try:
    import matplotlib
    matplotlib.use('Agg')                              # no GUI needed
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
except ImportError:                                    # pragma: no cover
    sys.exit('matplotlib is required:  pip install numpy matplotlib')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIGDIR = os.path.join(ROOT, 'manuscript', 'figures')

# Figures carry English labels: the manuscript is Persian but XeLaTeX
# embeds the PDF as-is, and Persian text inside matplotlib needs a shaping
# pass (arabic_reshaper + python-bidi) that is not worth the dependency.
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.linewidth': 0.8,
    'figure.dpi': 120,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.02,
})


def die(msg: str) -> None:
    sys.exit('ERROR: ' + msg)


def load_spectra(path: str) -> dict[str, np.ndarray]:
    if not os.path.isfile(path):
        die('%s not found -- run the Lumerical script first.' % path)
    with open(path, newline='', encoding='utf-8') as fh:
        rows = list(csv.reader(fh))
    header = [h.strip() for h in rows[0]]
    data = np.array([[float(v) for v in r] for r in rows[1:] if r], float)
    if data.size == 0:
        die('%s has a header but no data rows.' % path)
    return {name: data[:, i] for i, name in enumerate(header)}


def load_peaks(path: str) -> dict:
    """peaks.csv is quantity,value,unit -- return {quantity: float(value)}."""
    if not os.path.isfile(path):
        die('%s not found -- run the Lumerical script first.' % path)
    out = {}
    with open(path, newline='', encoding='utf-8') as fh:
        for row in list(csv.reader(fh))[1:]:
            if len(row) >= 2:
                try:
                    out[row[0].strip()] = float(row[1])
                except ValueError:
                    pass
    return out


def fig_purcell(sp: dict, pk: dict) -> str:
    """Figure 1 -- total Purcell factor spectrum."""
    lam, fp = sp['lambda_nm'], sp['Fp']
    i = int(np.argmax(fp))

    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.plot(lam, fp, color='#8b0000', lw=1.6)
    ax.plot(lam[i], fp[i], 'o', ms=5, mfc='none', mec='#8b0000', mew=1.4)
    ax.annotate(r'$F_p^{\max}=%.2f$ at $%.1f$ nm' % (fp[i], lam[i]),
                xy=(lam[i], fp[i]), xytext=(0.55, 0.82),
                textcoords='axes fraction', fontsize=10,
                arrowprops=dict(arrowstyle='->', lw=0.8, color='0.3'))
    ax.set_xlabel('Wavelength (nm)')
    ax.set_ylabel(r'Purcell factor  $F_p=\Gamma_{\rm tot}/\Gamma_0$')
    ax.set_xlim(lam.min(), lam.max())
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.25, lw=0.5)
    out = os.path.join(FIGDIR, 'Purcell_Spectrum.pdf')
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_radiated(sp: dict, pk: dict) -> str:
    """Figure 2 -- far-field enhancement T, with eta_a on a twin axis.

    Both peaks are marked so the red-shift discussed in section 4.2 is
    visible in the figure itself, not only in the text.
    """
    lam, t, fp = sp['lambda_nm'], sp['T'], sp['Fp']
    it, ifp = int(np.argmax(t)), int(np.argmax(fp))

    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.plot(lam, t, color='#00429d', lw=1.6, label=r'$T$ (radiated)')
    ax.plot(lam[it], t[it], 'o', ms=5, mfc='none', mec='#00429d', mew=1.4)
    ax.axvline(lam[ifp], color='#8b0000', ls='--', lw=0.9,
               label=r'$F_p$ peak (%.1f nm)' % lam[ifp])
    ax.axvline(lam[it], color='#00429d', ls=':', lw=0.9,
               label=r'$T$ peak (%.1f nm)' % lam[it])
    ax.annotate(r'$\Delta\lambda=%.1f$ nm' % (lam[it] - lam[ifp]),
                xy=(0.5 * (lam[ifp] + lam[it]), t[it] * 0.55),
                ha='center', fontsize=10, color='0.25')
    ax.set_xlabel('Wavelength (nm)')
    ax.set_ylabel(r'Radiated power enhancement  $T=P_{\rm rad}/P_0$')
    ax.set_xlim(lam.min(), lam.max())
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.25, lw=0.5)

    ax2 = ax.twinx()
    ax2.plot(lam, 100.0 * sp['eta_a'], color='#2e7d32', lw=1.2, alpha=0.85)
    ax2.set_ylabel(r'Apparent quantum efficiency $\eta_a$ (%)',
                   color='#2e7d32')
    ax2.tick_params(axis='y', colors='#2e7d32')
    ax2.set_ylim(bottom=0)

    ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
    out = os.path.join(FIGDIR, 'radiated_power_T.pdf')
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_nearfield(pk: dict) -> str | None:
    """Figure 3 -- |E|^2 map in the y=0 symmetry plane, log colour scale."""
    m_path = os.path.join(HERE, 'nearfield.csv')
    a_path = os.path.join(HERE, 'nearfield_axes.csv')
    if not (os.path.isfile(m_path) and os.path.isfile(a_path)):
        print('  skipped NearField_Profile.png (nearfield CSVs missing)')
        return None

    e2 = np.loadtxt(m_path, delimiter=',')       # rows = x, cols = z
    axes = {}
    with open(a_path, newline='', encoding='utf-8') as fh:
        for row in list(csv.reader(fh))[1:]:
            if len(row) >= 2:
                axes[row[0].strip()] = np.array(
                    [float(v) for v in row[1].split()], float)
    x, z = axes.get('x'), axes.get('z')
    if x is None or z is None:
        die('nearfield_axes.csv is missing the x or z row.')
    if e2.shape != (x.size, z.size):
        die('nearfield.csv is %s but axes imply %s -- mismatched export.'
            % (e2.shape, (x.size, z.size)))

    # Plot with z horizontal (the rod axis) so the elongated geometry fills
    # the frame; transposing puts z on the first axis for pcolormesh.
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    floor = max(e2[e2 > 0].min(), e2.max() * 1e-6)
    mesh = ax.pcolormesh(z, x, np.maximum(e2, floor),
                         norm=LogNorm(vmin=floor, vmax=e2.max()),
                         cmap='inferno', shading='auto')
    cb = fig.colorbar(mesh, ax=ax, pad=0.02)
    cb.set_label(r'$|E|^2$ (a.u., log scale)')

    # rod outline and dipole marker, drawn from the geometry in peaks.csv
    lt, dr, dg = pk.get('L_total'), pk.get('D_rod'), pk.get('d_gap')
    if lt and dr:
        r = dr / 2.0
        ax.plot([-lt / 2 + r, lt / 2 - r], [r, r], color='w', lw=0.8, alpha=0.7)
        ax.plot([-lt / 2 + r, lt / 2 - r], [-r, -r], color='w', lw=0.8,
                alpha=0.7)
        for zc in (-lt / 2 + r, lt / 2 - r):
            th = np.linspace(0, 2 * np.pi, 200)
            ax.plot(zc + r * np.cos(th), r * np.sin(th), color='w', lw=0.8,
                    alpha=0.7)
        if dg:
            ax.plot(lt / 2 + dg, 0, marker='*', ms=9, color='cyan',
                    mec='k', mew=0.4)

    ax.set_xlabel('z (nm)   -- rod axis')
    ax.set_ylabel('x (nm)')
    ax.set_aspect('equal')
    lam_fp = pk.get('lambda_Fp')
    if lam_fp:
        ax.set_title(r'$|E|^2$ at $\lambda_{\rm res}=%.1f$ nm' % lam_fp,
                     fontsize=10)
    out = os.path.join(FIGDIR, 'NearField_Profile.png')
    fig.savefig(out, dpi=400)
    plt.close(fig)
    return out


def write_numbers(sp: dict, pk: dict) -> str:
    """Emit the peak values formatted the way the .tex files phrase them."""
    lam, fp, t, eta = (sp['lambda_nm'], sp['Fp'], sp['T'], sp['eta_a'])
    ifp, it = int(np.argmax(fp)), int(np.argmax(t))
    loss = fp[ifp] - t[ifp]

    lines = [
        'Numbers for the manuscript text (generated by make_figures.py)',
        '=' * 62,
        '',
        'Fp_max            = %.2f      at lambda = %.1f nm' % (fp[ifp], lam[ifp]),
        'T_max             = %.2f      at lambda = %.1f nm' % (t[it], lam[it]),
        'red shift         = %.1f nm' % (lam[it] - lam[ifp]),
        'eta_a at Fp peak  = %.1f %%' % (100.0 * eta[ifp]),
        'non-radiative     = %.1f %%' % (100.0 * (1.0 - eta[ifp])),
        'Fp - T at peak    = %.2f' % loss,
        '',
        'Geometry used:',
        '  L_total = %s nm   D_rod = %s nm   R_cap = %s nm   d_gap = %s nm'
        % (pk.get('L_total'), pk.get('D_rod'), pk.get('R_cap'),
           pk.get('d_gap')),
        '  mesh accuracy = %s   dx_fine = %s nm'
        % (pk.get('mesh_accuracy'), pk.get('dx_fine')),
        '  energy-balance error (median) = %s %%'
        % pk.get('balance_err_median'),
        '',
        'Replace in manuscript/sections/03_methodology.tex:',
        '  $L$   -> %s nm' % pk.get('L_total'),
        '  $D$   -> %s nm' % pk.get('D_rod'),
        '  $R$   -> %s nm  (= D/2)' % pk.get('R_cap'),
        '',
        'CAUTION: the .tex files currently quote Fp=2020.48 @ 607.9 nm,',
        'T=143.42 @ 615.1 nm, eta_a=7.1 %, loss=1877.06. If the numbers',
        'above differ, every one of those figures must be updated -- they',
        'appear in main.tex (abstract), 04_results.tex (4.1-4.3 and 4.5),',
        'and 05_conclusion.tex.',
    ]
    out = os.path.join(HERE, '_numbers_for_text.txt')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    return out


def main() -> None:
    os.makedirs(FIGDIR, exist_ok=True)
    sp = load_spectra(os.path.join(HERE, 'spectra.csv'))
    pk = load_peaks(os.path.join(HERE, 'peaks.csv'))

    for col in ('lambda_nm', 'Fp', 'T', 'eta_a'):
        if col not in sp:
            die('spectra.csv is missing the %r column.' % col)

    made = [fig_purcell(sp, pk), fig_radiated(sp, pk), fig_nearfield(pk)]
    made.append(write_numbers(sp, pk))
    for path in made:
        if path:
            print('wrote', os.path.relpath(path, ROOT))

    print('\nNext: run tools\\figures_prep.py to refresh the web '
          'PNGs, then tools\\make_review_zip.py to rebuild the HTML '
          'package (PDF builds are blocked: no TeX engine on this box)')


if __name__ == '__main__':
    main()

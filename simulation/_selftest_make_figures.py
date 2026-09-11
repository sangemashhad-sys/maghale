r"""Self-test for make_figures.py using synthetic data (no Lumerical needed).

Creates fake spectra.csv / peaks.csv / nearfield*.csv in a temporary folder,
runs the three plotting functions against them, asserts the outputs exist and
are non-trivial, then removes everything it made.

    python simulation/_selftest_make_figures.py

This file is disposable: delete it once the real simulation data is in place.
"""
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def make_fake_inputs(folder: str) -> None:
    """Two Lorentzians with deliberately offset peaks, like the real physics."""
    lam = np.linspace(450.0, 800.0, 401)

    def lorentz(x0, w, a):
        return a / (1.0 + ((lam - x0) / w) ** 2)

    fp = lorentz(607.9, 22.0, 2020.48) + 5.0
    t = lorentz(615.1, 26.0, 143.42) + 0.5
    eta = t / fp
    a_metal = fp - t

    with open(os.path.join(folder, 'spectra.csv'), 'w', encoding='utf-8') as fh:
        fh.write('lambda_nm,Fp,T,eta_a,A_metal\n')
        for k in range(lam.size):
            fh.write('%.6g,%.6g,%.6g,%.6g,%.6g\n'
                     % (lam[k], fp[k], t[k], eta[k], a_metal[k]))

    ifp = int(np.argmax(fp))
    it = int(np.argmax(t))
    rows = [
        ('Fp_max', fp[ifp]), ('lambda_Fp', lam[ifp]),
        ('T_max', t[it]), ('lambda_T', lam[it]),
        ('red_shift', lam[it] - lam[ifp]),
        ('eta_a_at_Fp_peak', eta[ifp]),
        ('loss_at_Fp_peak', fp[ifp] - t[ifp]),
        ('L_total', 60.0), ('D_rod', 20.0), ('R_cap', 10.0), ('d_gap', 5.0),
        ('mesh_accuracy', 3.0), ('dx_fine', 2.0),
        ('balance_err_median', 0.8),
    ]
    with open(os.path.join(folder, 'peaks.csv'), 'w', encoding='utf-8') as fh:
        fh.write('quantity,value,unit\n')
        for name, val in rows:
            fh.write('%s,%.6g,-\n' % (name, val))

    # near-field map: bright lobes at both rod tips
    x = np.linspace(-40.0, 40.0, 81)
    z = np.linspace(-60.0, 70.0, 131)
    zz, xx = np.meshgrid(z, x)
    e2 = (1.0
          + 4e3 * np.exp(-(((zz - 25.0) ** 2 + xx ** 2) / 30.0))
          + 4e3 * np.exp(-(((zz + 25.0) ** 2 + xx ** 2) / 30.0)))
    np.savetxt(os.path.join(folder, 'nearfield.csv'), e2, delimiter=',',
               fmt='%.6g')
    with open(os.path.join(folder, 'nearfield_axes.csv'), 'w',
              encoding='utf-8') as fh:
        fh.write('axis,values_nm\n')
        fh.write('x,' + ' '.join('%.6g' % v for v in x) + '\n')
        fh.write('z,' + ' '.join('%.6g' % v for v in z) + '\n')


def main() -> int:
    figdir = os.path.join(ROOT, 'manuscript', 'figures')
    expected = ['Purcell_Spectrum.pdf', 'radiated_power_T.pdf',
                'NearField_Profile.png']
    preexisting = {n for n in expected
                   if os.path.isfile(os.path.join(figdir, n))}
    if preexisting:
        print('REFUSING to run: real figures already exist:', preexisting)
        print('Delete them first if you really want to overwrite with fakes.')
        return 2

    stash = tempfile.mkdtemp(prefix='lsf_stash_')
    created = ['spectra.csv', 'peaks.csv', 'nearfield.csv',
               'nearfield_axes.csv']
    try:
        make_fake_inputs(HERE)
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, 'make_figures.py')],
            capture_output=True, text=True)
        print(proc.stdout)
        if proc.returncode != 0:
            print('make_figures.py FAILED:\n' + proc.stderr)
            return 1

        ok = True
        for name in expected:
            path = os.path.join(figdir, name)
            if not os.path.isfile(path):
                print('MISSING output:', name)
                ok = False
            elif os.path.getsize(path) < 4096:
                print('SUSPICIOUSLY SMALL (%d bytes):' % os.path.getsize(path),
                      name)
                ok = False
            else:
                print('OK %-24s %6.1f KB'
                      % (name, os.path.getsize(path) / 1024.0))

        nums = os.path.join(HERE, '_numbers_for_text.txt')
        if not os.path.isfile(nums):
            print('MISSING _numbers_for_text.txt')
            ok = False
        else:
            text = open(nums, encoding='utf-8').read()
            for token in ('2020.48', '607.9', '143.42', '615.1'):
                if token not in text:
                    print('_numbers_for_text.txt lost the value', token)
                    ok = False
            print('OK _numbers_for_text.txt reproduces the expected peaks')

        print('\nSELFTEST', 'PASSED' if ok else 'FAILED')
        return 0 if ok else 1
    finally:
        # remove the fake figures so they can never reach the PDF
        for name in expected:
            path = os.path.join(figdir, name)
            if os.path.isfile(path):
                os.remove(path)
        for name in created + ['_numbers_for_text.txt']:
            path = os.path.join(HERE, name)
            if os.path.isfile(path):
                os.remove(path)
        shutil.rmtree(stash, ignore_errors=True)
        print('cleaned up synthetic inputs, figures and _numbers_for_text.txt')


if __name__ == '__main__':
    sys.exit(main())

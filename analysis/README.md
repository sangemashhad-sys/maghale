# analysis/

اسکریپت‌های تحلیل و شکل‌سازی از داده‌ی خام اجرای دوم (`../New folder (2)/`).

| فایل | کار |
|---|---|
| `mie_dipole_sphere.py` | حل تحلیلی می برای دوقطبی شعاعی کنار کره‌ی طلا (Ruppin 1982 / Kim–Leung–George 1988) و مقایسه با FDTD حالت D → `D_sphere_mie_vs_fdtd.{png,txt}` و `manuscript/figures/D_sphere_mie_vs_fdtd.pdf` |
| `make_run2_figures.py` | شکل‌های داده‌محور مقاله: `fig_spectra_all`, `fig_efficiency`, `fig_freespace_B`, `fig_nearfield_CD` در `manuscript/figures/` (+ PNG در `figures/web/`) |

نیازمندی‌ها: `numpy scipy matplotlib`. حالت A فایل خام ندارد؛ وقتی `A_baseline_spectra.txt` رسید، در `make_run2_figures.py` آن را مثل C و D بارگذاری کن.

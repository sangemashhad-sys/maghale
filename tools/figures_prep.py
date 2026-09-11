#!/usr/bin/env python3
"""آماده‌سازی شکل‌ها  —  اجرا:  python tools/figures_prep.py [--clean]

شکل‌های خروجی Lumerical برداری و در قالب PDF هستند. XeLaTeX همان PDF را
مستقیم درج می‌کند و بهترین کیفیت را می‌دهد، اما مرورگر PDF را داخل <img>
نشان نمی‌دهد. پس از هر PDF یک PNG با تفکیک بالا در
manuscript/figures/web/ ساخته می‌شود؛ tools/tex2html.py هنگام ساخت
پیش‌نمایش خودش همان را برمی‌دارد. فایل‌های PNG اصلی کپی می‌شوند تا مسیر
شکل‌ها در پیش‌نمایش یکدست بماند.

سوئیچ --clean جریان محتوای PDF را هم بازنویسی می‌کند: خروجی
GL2PS 1.3.8 (کتابخانه‌ی تصویرگیری VTK که Lumerical از آن استفاده می‌کند)
عملگر شفافیت را به‌جای گذاشتن در ExtGState داخل جریان محتوا می‌نویسد
(`ca`) که خلاف مشخصات PDF است و هشدار «unknown keyword» می‌دهد.
بازنویسی آن را حذف می‌کند تا xdvipdfmx بی‌دردسر شکل را درج کند. نسخه‌ی
دست‌نخورده با پسوند .orig.pdf کنار فایل نگه داشته می‌شود و برای اطمینان،
تصویر پیش و پس از بازنویسی پیکسل‌به‌پیکسل مقایسه و اختلافش گزارش می‌شود.

نیازمندی: PyMuPDF  (pip install pymupdf)
جانشین بدون پایتون:  pdftocairo -png -r 200 figures/X.pdf figures/web/X
"""
import os
import shutil
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

try:
    import fitz                                    # PyMuPDF
except ImportError:
    sys.exit('PyMuPDF لازم است:  pip install pymupdf')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, 'manuscript', 'figures')
WEB = os.path.join(FIG, 'web')
DPI = 200


def render(path):
    """صفحه‌ی نخست را به Pixmap تبدیل می‌کند."""
    with fitz.open(path) as doc:
        return doc[0].get_pixmap(dpi=DPI)


def diff(a, b):
    """بیشترین اختلاف یک بایت میان دو تصویر هم‌اندازه (۰ تا ۲۵۵)."""
    if (a.width, a.height, a.n) != (b.width, b.height, b.n):
        return 255
    sa, sb = a.samples, b.samples
    return max((abs(x - y) for x, y in zip(sa, sb)), default=0)


def clean_pdf(path):
    """PDF را بازنویسی و اختلاف تصویری را برمی‌گرداند (None = رد شد)."""
    backup = path[:-4] + '.orig.pdf'
    if not os.path.isfile(backup):
        shutil.copy2(path, backup)
    before = render(backup)
    tmp = path + '.tmp'
    with fitz.open(backup) as doc:
        doc.save(tmp, clean=True, garbage=4, deflate=True, pretty=False)
    after = render(tmp)
    d = diff(before, after)
    if d > 8:                       # بازنویسی ظاهر شکل را عوض کرده: قبول نکن
        os.remove(tmp)
        return None
    os.replace(tmp, path)
    return d


def main():
    do_clean = '--clean' in sys.argv[1:]
    if not os.path.isdir(FIG):
        sys.exit('پوشه یافت نشد: %s' % FIG)
    os.makedirs(WEB, exist_ok=True)

    names = sorted(n for n in os.listdir(FIG)
                   if n.lower().endswith(('.pdf', '.png'))
                   and not n.lower().endswith('.orig.pdf'))
    if not names:
        sys.exit('هیچ شکلی در %s نیست.' % FIG)

    for name in names:
        src = os.path.join(FIG, name)
        if name.lower().endswith('.png'):
            shutil.copy2(src, os.path.join(WEB, name))
            print('کپی شد:  web/%s' % name)
            continue
        if do_clean:
            d = clean_pdf(src)
            print('بازنویسی %s: %s' % (
                name, 'بیشترین اختلاف پیکسل %d (پشتیبان .orig.pdf)' % d
                if d is not None else 'رد شد، ظاهر عوض می‌شد'))
        out = os.path.join(WEB, name[:-4] + '.png')
        pix = render(src)
        pix.save(out)
        print('ساخته شد: web/%s  (%d×%d، %d dpi)'
              % (os.path.basename(out), pix.width, pix.height, DPI))

    print('\nگام بعد:  python tools/tex2html.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

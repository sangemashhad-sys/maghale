# -*- coding: utf-8 -*-
"""سازنده‌ی اسلایدهای ارائه.

ورودی:  slides_template.html (کنار همین فایل)
خروجی:  slides.html

دو کار می‌کند:
  ۱. قلم وزیرمتن را به‌صورت data: داخل خود HTML جاسازی می‌کند تا اسلایدها
     بدون اینترنت و حتی با دوبار کلیک روی فایل (file://) درست دیده شوند؛
     کروم بارگیری قلم از فایل کنار را با خطای CORS رد می‌کند.
  ۲. نشانی MathJax محلی را می‌گذارد (manuscript/vendor/mathjax) تا برای
     فرمول‌ها نیازی به CDN نباشد.

کاربرد:
    python build_slides.py
"""
from __future__ import annotations

import base64
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
TPL = HERE / 'slides_template.html'
OUT = HERE / 'slides.html'

FONT_REG = ROOT / 'manuscript' / 'fonts' / 'Vazirmatn-Regular.woff2'
FONT_BOLD = ROOT / 'manuscript' / 'fonts' / 'Vazirmatn-Bold.woff2'
MATHJAX = '../manuscript/vendor/mathjax/tex-svg.js'


def data_uri(path: pathlib.Path) -> str:
    if not path.is_file():
        sys.stderr.write('هشدار: قلم یافت نشد %s\n' % path)
        return ''
    b64 = base64.b64encode(path.read_bytes()).decode('ascii')
    return 'data:font/woff2;base64,' + b64


def main() -> int:
    doc = TPL.read_text(encoding='utf-8')
    doc = doc.replace('__FONT_REG__', data_uri(FONT_REG))
    doc = doc.replace('__FONT_BOLD__', data_uri(FONT_BOLD))
    doc = doc.replace('__MJ__', MATHJAX)
    left = [t for t in ('__FONT_REG__', '__FONT_BOLD__', '__MJ__') if t in doc]
    if left:
        sys.stderr.write('هشدار: جانمایش‌های جای‌نمانده: %s\n' % left)
    OUT.write_text(doc, encoding='utf-8', newline='\n')
    n = doc.count('class="slide')
    print('نوشته شد: %s  (%d کیلوبایت، %d اسلاید)'
          % (OUT, len(doc.encode('utf-8')) // 1024, n))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

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
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
TPL = HERE / 'slides_template.html'
OUT = HERE / 'slides.html'

FONT_REG = ROOT / 'manuscript' / 'fonts' / 'Vazirmatn-Regular.woff2'
FONT_BOLD = ROOT / 'manuscript' / 'fonts' / 'Vazirmatn-Bold.woff2'
MJ_PATH = ROOT / 'manuscript' / 'vendor' / 'mathjax' / 'tex-svg.js'
FIG_WEB = ROOT / 'manuscript' / 'figures' / 'web'


def data_uri(path: pathlib.Path, mime: str) -> str:
    if not path.is_file():
        sys.stderr.write('هشدار: فایل یافت نشد %s\n' % path)
        return ''
    b64 = base64.b64encode(path.read_bytes()).decode('ascii')
    return 'data:%s;base64,%s' % (mime, b64)


def main() -> int:
    doc = TPL.read_text(encoding='utf-8')
    doc = doc.replace('__FONT_REG__', data_uri(FONT_REG, 'font/woff2'))
    doc = doc.replace('__FONT_BOLD__', data_uri(FONT_BOLD, 'font/woff2'))

    # شکل‌ها: نشانی نسبی در نمایشگر تک‌فایلی کار نمی‌کند؛ data: می‌کنیم.
    def img_sub(m):
        return 'src="%s"' % data_uri(FIG_WEB / m.group(1), 'image/png')
    doc, n_img = re.subn(r'src="\.\./manuscript/figures/web/([^"]+)"',
                         img_sub, doc)

    # MathJax: کل bundle را درون‌خطی می‌کنیم تا اسلایدها هیچ وابستگی بیرونی
    # نداشته باشند (فایل رشته‌ی </script ندارد).
    tag = '<script defer src="__MJ__"></script>'
    if MJ_PATH.is_file() and '</script' not in MJ_PATH.read_text(
            encoding='utf-8').lower():
        js = MJ_PATH.read_text(encoding='utf-8')
        doc = doc.replace(tag,
                          '<script>/* mathjax-inline */\n%s\n</script>' % js)
    else:
        doc = doc.replace('__MJ__', '../manuscript/vendor/mathjax/tex-svg.js')

    left = [t for t in ('__FONT_REG__', '__FONT_BOLD__', '__MJ__') if t in doc]
    if left:
        sys.stderr.write('هشدار: جانمایش‌های جای‌نمانده: %s\n' % left)
    ext = re.findall(r'<img src="(?!data:)[^"]+"', doc)
    if ext:
        sys.stderr.write('هشدار: تصویر بیرونی جای‌مانده: %s\n' % ext)
    OUT.write_text(doc, encoding='utf-8', newline='\n')
    n = doc.count('class="slide')
    print('نوشته شد: %s  (%d کیلوبایت، %d اسلاید)'
          % (OUT, len(doc.encode('utf-8')) // 1024, n))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

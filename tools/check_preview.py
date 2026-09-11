#!/usr/bin/env python3
"""بازبینی پیش‌نمایش HTML — اجرا:  python tools/check_preview.py

چیزهایی که بررسی می‌شود (هیچ‌کدام به اینترنت یا TeX نیاز ندارد):
  ۱. هر href="#x" یک id="x" داشته باشد (لنگرهای شکسته، مثل رابطه‌ی دومِ
     یک align که در گذشته id نمی‌گرفت)
  ۲. قلم به‌شکل data: جاسازی شده باشد، وگرنه کروم در file:// آن را
     بارگیری نمی‌کند و متن با قلم پیش‌فرض سیستم دیده می‌شود
  ۳. MathJax محلی باشد، نه CDN
  ۴. هیچ دستور لاتک ترجمه‌نشده‌ای بیرون از ریاضی نمانده باشد
خروجی: چاپ در ترمینال؛ کد بازگشت ۱ اگر ایرادی پیدا شود.
"""
import io
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, 'manuscript', 'preview.html')
ROOT_HTML = os.path.join(ROOT, 'index.html')


def main():
    if not os.path.isfile(HTML):
        sys.stderr.write('پیش‌نمایش ساخته نشده؛ اول tex2html.py را اجرا کنید.\n')
        return 1
    doc = io.open(HTML, encoding='utf-8').read()
    bad = []

    ids = set(re.findall(r'id="([^"]+)"', doc))
    hrefs = set(re.findall(r'href="#([^"]+)"', doc))
    missing = sorted(hrefs - ids)
    print('لنگرهای بی‌هدف: %s' % (missing or 'ندارد'))
    if missing:
        bad.append('لنگر')

    n_font = doc.count('data:font/woff2')
    left = re.findall(r'url\("[^"]*\.woff2"\)', doc)
    print('قلم جاسازی‌شده: %d @font-face | نشانی فایلی باقی‌مانده: %s'
          % (n_font, left or 'ندارد'))
    if n_font < 2 or left:
        bad.append('قلم')

    local_mj = 'vendor/mathjax' in doc
    print('MathJax محلی: %s' % local_mj)
    if not local_mj:
        bad.append('MathJax')

    # Root index must prefix local assets with manuscript/, while #anchors
    # must remain local to the same document. This keeps MathJax working and
    # preserves equation/section links when index.html is opened directly.
    root_ok = False
    if os.path.isfile(ROOT_HTML):
        root_doc = io.open(ROOT_HTML, encoding='utf-8').read()
        root_ok = '<base ' not in root_doc
        assets = re.findall(r'(?:src|href)="([^"#:]+)"', root_doc)
        for rel in assets:
            if rel.startswith(('data:', 'http', 'mailto:', '/')):
                continue
            candidate = os.path.join(ROOT, rel.replace('/', os.sep))
            if not rel.startswith('manuscript/') or not os.path.isfile(candidate):
                root_ok = False
                break
    print('نسخه‌ی ریشه و مسیر دارایی‌ها: %s'
          % ('سالم' if root_ok else 'خراب'))
    if not root_ok:
        bad.append('index ریشه')

    plain = re.sub(r'<script.*?</script>|<div class="eq".*?</div>'
                   r'|\\\(.*?\\\)', '', doc, flags=re.S)
    leftover = sorted(set(re.findall(r'\\([a-zA-Z]+)', plain)))
    print('دستور لاتک ترجمه‌نشده: %s'
          % (', '.join('\\' + x for x in leftover) if leftover else 'ندارد'))
    if leftover:
        bad.append('لاتک')

    print('\nنتیجه: %s' % ('ایراد در ' + '، '.join(bad) if bad else 'سالم'))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())

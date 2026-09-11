#!/usr/bin/env python3
"""یک‌بار دانلود MathJax و نگه‌داشتنش کنار مقاله — اجرا:

    python tools/vendor_mathjax.py

چرا؟ `preview.html` فرمول‌ها را با MathJax رندر می‌کند. اگر آن را از CDN
بگیرد، پیش‌نمایش بدون اینترنت (یا روی لپ‌تاپ داورِ بدون اینترنت) فرمول‌ها
را خالی نشان می‌دهد. بسته‌ی `tex-svg.js` تنها یک فایل است و قلم را هم
درون خودش به‌شکل مسیرهای SVG دارد، پس همین یک فایل برای رندرِ کاملاً
آفلاین کافی است.

خروجی: manuscript/vendor/mathjax/tex-svg.js

اگر دانلود نشد، `tools/tex2html.py` خودش سراغ CDN می‌رود و پیش‌نمایش
همچنان کار می‌کند — فقط برای فرمول‌ها به اینترنت نیاز دارد.
"""
import os
import sys
import time
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, 'manuscript', 'vendor', 'mathjax', 'tex-svg.js')

# نسخه ثابت پین شده تا خروجی تکرارپذر بماند
VERSION = '3.2.2'
MIRRORS = [
    'https://cdn.jsdelivr.net/npm/mathjax@%s/es5/tex-svg.js' % VERSION,
    'https://unpkg.com/mathjax@%s/es5/tex-svg.js' % VERSION,
    'https://cdnjs.cloudflare.com/ajax/libs/mathjax/%s/es5/tex-svg.js' % VERSION,
]

MIN_BYTES = 400 * 1024      # نسخه‌ی واقعی ~۱٫۵ مگابایت است؛ کمتر از این ناقص است


def already_there():
    return os.path.isfile(DEST) and os.path.getsize(DEST) >= MIN_BYTES


def fetch(url, timeout=180):
    req = urllib.request.Request(url, headers={'User-Agent': 'curl/8'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data, time.time() - t0


def main():
    if already_there():
        print('از قبل موجود است: %s (%d کیلوبایت)'
              % (os.path.relpath(DEST, ROOT), os.path.getsize(DEST) // 1024))
        return 0

    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    for url in MIRRORS:
        print('تلاش: %s' % url)
        try:
            data, secs = fetch(url)
        except Exception as exc:                # noqa: BLE001 — هر خطای شبکه
            print('   نشد: %s' % exc)
            continue
        if len(data) < MIN_BYTES:
            print('   فایل ناقص (%d بایت) — رد شد' % len(data))
            continue
        if b'MathJax' not in data[:20000]:
            print('   محتوا MathJax نیست — رد شد')
            continue
        with open(DEST, 'wb') as f:
            f.write(data)
        print('نوشته شد: %s (%d کیلوبایت، %.1f ثانیه)'
              % (os.path.relpath(DEST, ROOT), len(data) // 1024, secs))
        return 0

    print('هیچ آینه‌ای پاسخ نداد. پیش‌نمایش با CDN ساخته می‌شود؛ برای'
          ' نسخه‌ی آفلاین دوباره تلاش کنید.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())

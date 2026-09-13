# -*- coding: utf-8 -*-
"""نسخه‌ی نهایی تک‌فایلی مقاله:  python3 tools/make_final_html.py

کارها:
  ۱. `tools/tex2html.py --final` را اجرا می‌کند → manuscript/final.html
     (خروجی همان‌جا کاملاً خودبسنده است: قلم، شکل‌ها و MathJax جاسازی شده؛
     جاسازی از نسخه‌ی شاخه‌ی arena/01a09b2c به tools/tex2html.py منتقل شد تا
     preview و final هر دو تک‌فایل باشند).
  ۲. رونوشت‌های توزیعی می‌سازد:
       - مقاله_نسخه_نهایی.html      (ریشه‌ی مخزن، برای ارسال/آفلاین)
       - maghale-preview/final.html (بسته‌ی بازبینی)
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MS = os.path.join(ROOT, 'manuscript')
SRC = os.path.join(MS, 'final.html')
COPIES = [os.path.join(ROOT, 'مقاله_نسخه_نهایی.html'),
          os.path.join(ROOT, 'maghale-preview', 'final.html')]


def main():
    subprocess.check_call([sys.executable, os.path.join(ROOT, 'tools',
                                                        'tex2html.py'),
                           '--final'])
    for dst in COPIES:
        d = os.path.dirname(dst)
        if not os.path.isdir(d):
            continue
        shutil.copyfile(SRC, dst)
        print('رونوشت: %s' % dst)
    print('اندازه: %d کیلوبایت' % (os.path.getsize(SRC) // 1024))


if __name__ == '__main__':
    main()

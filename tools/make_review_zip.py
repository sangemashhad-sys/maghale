#!/usr/bin/env python3
"""بسته‌ی زیپِ قابل‌ارسال برای بازبینی مقاله — اجرا:

    python tools/make_review_zip.py

خروجی: maghale-preview.zip در ریشه‌ی مخزن.

گیرنده فقط زیپ را باز می‌کند و روی `index.html` دوبار کلیک می‌کند؛ نه
اینترنت لازم است، نه نصب قلم، نه LaTeX.

چه چیزی داخل زیپ می‌رود؟
  index.html                 پیش‌نمایش (همان manuscript/preview.html)
  figures/web/*.png          شکل‌ها برای نمایش در مرورگر
  figures/*.pdf              نسخه‌ی برداری، برای کلیک روی شکل
  vendor/mathjax/tex-svg.js  رندر فرمول‌ها به‌صورت آفلاین
  README.txt                 راهنمای کوتاه برای گیرنده

چرا قلم داخل خود HTML جاسازی می‌شود و فایل `.woff2` جدا نمی‌رود؟
کروم صفحه‌های `file://` را «مبدأ ناشناس» می‌شمارد و بارگیری قلم از کنار
فایل را با خطای CORS رد می‌کند؛ در آن حالت متن با قلم پیش‌فرض سیستم
دیده می‌شود. قلمِ جاسازی‌شده به‌شکل `data:` این محدودیت را ندارد و در
همه‌ی مرورگرها یکسان کار می‌کند. هزینه‌اش حدود ۱۳۰ کیلوبایت است.
"""
import base64
import os
import re
import subprocess
import sys
import zipfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MS = os.path.join(ROOT, 'manuscript')
HTML = os.path.join(MS, 'preview.html')
ZIP = os.path.join(ROOT, 'maghale-preview.zip')
TOP = 'maghale-preview'          # نام پوشه‌ی داخل زیپ

README = """\
پیش‌نمایش مقاله برای بازبینی
============================

۱) این پوشه را از حالت زیپ خارج کنید (Extract All).
۲) روی فایل  index.html  دوبار کلیک کنید تا در مرورگر باز شود.

نیازی به اینترنت، نصب قلم یا نرم‌افزار خاصی نیست. کل بسته آفلاین کار
می‌کند و هیچ فایلی روی سیستم شما نصب نمی‌شود.

نکته‌های بازبینی
---------------
* این نسخه فقط برای «خواندن متن» است. صفحه‌آرایی، شماره‌ی صفحه و شکست
  سطرها در نسخه‌ی نهایی PDF (که با XeLaTeX ساخته می‌شود) تعیین می‌شود،
  پس درباره‌ی ظاهر صفحه ایراد نگیرید — درباره‌ی محتوا بگیرید.
* عدد خاکستری کنار هر پاراگراف، شماره‌ی همان پاراگراف است. در بازخورد
  به همان شماره ارجاع دهید، مثلاً: «پاراگراف ۱۴، جمله‌ی دوم». با کلیک
  روی آن عدد، نشانی همان پاراگراف در نوار آدرس مرورگر می‌آید و
  می‌توانید همان لینک را بفرستید.
* با کلیک روی هر نمودار، نسخه‌ی برداری (PDF) همان شکل باز می‌شود.
* فرمول‌ها همان کد LaTeX مقاله‌اند که در مرورگر رندر شده‌اند؛ اگر
  فرمولی درست دیده نشد، لطفاً شماره‌ی رابطه را بنویسید.
* مراجع پایین صفحه شماره‌گذاری شده‌اند و شماره‌های داخل متن به آن‌ها
  لینک است.

اگر مرورگر شما قدیمی است (اینترنت اکسپلورر) صفحه درست دیده نمی‌شود؛
با Firefox، Chrome یا Edge باز کنید.
"""


def run_tex2html():
    """پیش‌نمایش را دوباره می‌سازد تا زیپ از آخرین متن .tex باشد."""
    cmd = [sys.executable, os.path.join(ROOT, 'tools', 'tex2html.py')]
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    for line in (p.stdout or '').splitlines():
        print('  | ' + line)
    if p.returncode != 0:
        sys.stderr.write((p.stderr or '') + '\n')
        raise SystemExit('tex2html.py با خطا تمام شد (کد %d)' % p.returncode)


def inline_fonts(doc):
    """url("fonts/X.woff2") را با data: جایگزین می‌کند.

    از نسخه‌ی کنونی به بعد این کار را خودِ `tex2html.py` انجام می‌دهد تا
    `manuscript/preview.html` هم در `file://` قلم داشته باشد؛ این تابع
    فقط برای سازگاری با خروجی‌های قدیمی مانده است.
    """
    done = []

    def sub(m):
        rel = m.group(1)
        path = os.path.join(MS, rel.replace('/', os.sep))
        if not os.path.isfile(path):
            sys.stderr.write('هشدار: قلم یافت نشد: %s\n' % rel)
            return m.group(0)
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('ascii')
        done.append(rel)
        return 'url("data:font/woff2;base64,%s")' % b64

    doc = re.sub(r'url\("([^"]+\.woff2)"\)', sub, doc)
    return doc, done


def assets(doc):
    """نشانی فایل‌های محلیِ ارجاع‌شده در HTML را برمی‌گرداند."""
    found = []
    for rel in re.findall(r'(?:src|href)="([^"#:]+)"', doc):
        if rel.startswith(('data:', 'http', 'mailto:', '/')):
            continue
        path = os.path.join(MS, rel.replace('/', os.sep))
        if os.path.isfile(path) and rel not in found:
            found.append(rel)
    return found


def main():
    print('۱) ساخت پیش‌نمایش از فایل‌های .tex')
    run_tex2html()

    doc = open(HTML, encoding='utf-8').read()

    print('۲) بررسی جاسازی قلم')
    if 'data:font/woff2' in doc:
        print('   قلم پیش‌تر توسط tex2html.py جاسازی شده است.')
    else:
        doc, fonts = inline_fonts(doc)
        for rel in fonts:
            print('   قلمِ جاسازی‌شده: %s' % rel)
        if not fonts:
            sys.stderr.write('هشدار: هیچ قلمی جاسازی نشد؛ متن با قلم پیش‌فرض'
                             ' سیستم دیده می‌شود.\n')

    files = assets(doc)
    if not any(a.endswith('.js') for a in files):
        sys.stderr.write('هشدار: MathJax محلی نیست، پیش‌نمایش برای فرمول‌ها'
                         ' به اینترنت نیاز خواهد داشت.\n'
                         '        اول این را اجرا کنید:'
                         ' python tools/vendor_mathjax.py\n')

    print('۳) نوشتن زیپ')
    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(TOP + '/index.html', doc.encode('utf-8'))
        # ویندوز Notepad بدون BOM فارسیِ UTF-8 را درست نشان نمی‌دهد
        z.writestr(TOP + '/README.txt',
                   '\ufeff' + README.replace('\n', '\r\n'))
        for rel in files:
            z.write(os.path.join(MS, rel.replace('/', os.sep)),
                    TOP + '/' + rel)
            print('   + %s' % rel)

    kb = os.path.getsize(ZIP) // 1024
    print('\nآماده است: %s  (%d کیلوبایت، %d فایل)'
          % (os.path.relpath(ZIP, ROOT), kb, len(files) + 2))
    print('همین یک فایل را بفرستید؛ گیرنده آن را باز می‌کند و روی'
          ' index.html دوبار کلیک می‌کند.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

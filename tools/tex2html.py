#!/usr/bin/env python3
"""پیش‌نمایش HTML از متن مقاله  —  اجرا:  python tools/tex2html.py

خروجی: manuscript/preview.html  (با دوبار کلیک در مرورگر باز می‌شود)

هدف فقط «خواندن متن» است، نه صفحه‌آرایی. فرمول‌ها با MathJax از همان کد
LaTeX رندر می‌شوند، پس عددها و روابط دقیقاً همان چیزی‌اند که در .tex هست.
خروجی نهایی PDF همچنان کار XeLaTeX است.

منبع یگانه‌ی متن، همان فایل‌های .tex هستند؛ این اسکریپت چیزی را کپی
نمی‌کند. متن را در .tex عوض کنید و دوباره اجرا کنید.
"""
import base64
import html
import os
import re
import sys

# پیام‌ها فارسی‌اند؛ اگر خروجی به فایل هدایت شود کدپیج ویندوز آن‌ها را
# نمی‌پذیرد، پس همین ابتدا روی UTF-8 قفلش می‌کنیم.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

MS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  'manuscript')
OUT = os.path.join(MS, 'preview.html')
ROOT_OUT = os.path.join(os.path.dirname(MS), 'index.html')

# MathJax: اگر نسخه‌ی محلی (tools/vendor_mathjax.py) موجود باشد همان استفاده
# می‌شود تا پیش‌نمایش بدون اینترنت هم فرمول‌ها را نشان دهد؛ وگرنه CDN.
MATHJAX_LOCAL = os.path.join('vendor', 'mathjax', 'tex-svg.js')
MATHJAX_CDN = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js'

STASH = []          # قطعه‌های آماده‌ی HTML یا ریاضی که نباید دست‌کاری شوند
LABELS = {}         # label -> شماره‌ی نمایشی
CITES = {}          # کلید bib -> شماره‌ی ارجاع
TOC = []            # (سطح, شماره, عنوان, لنگر)
N = {'sec': 0, 'sub': 0, 'fig': 0, 'tab': 0, 'eq': 0, 'par': 0}


def keep(chunk):
    """قطعه را کنار می‌گذارد و یک نشانه‌ی بی‌خطر برمی‌گرداند."""
    STASH.append(chunk)
    return '\x00%d\x00' % (len(STASH) - 1)


def keep_block(chunk):
    """مثل keep، ولی با خط خالی دو طرف.

    در .tex خطِ تک‌`%` پیش و پس از \\begin{equation} فاصله‌ی اضافی را حذف
    می‌کند و رابطه بخشی از همان پاراگراف می‌ماند. در HTML این کار <div> را
    داخل <p> می‌بَرد که نامعتبر است، پس اینجا شکست پاراگراف را تحمیل می‌کنیم.
    """
    return '\n\n' + keep(chunk) + '\n\n'


def unkeep(text):
    for _ in range(5):                      # قطعه‌ها می‌توانند تودرتو باشند
        new = re.sub(r'\x00(\d+)\x00', lambda m: STASH[int(m.group(1))], text)
        if new == text:
            return text
        text = new
    return text


def group(text, i):
    """یک گروه متوازن {...} را از موقعیت i می‌خواند."""
    depth = 0
    j = i
    while j < len(text):
        if text[j] == '\\':
            j += 2
            continue
        if text[j] == '{':
            depth += 1
        elif text[j] == '}':
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j + 1
        j += 1
    return text[i + 1:], len(text)


def strip_comments(text):
    """درصدهای توضیحی را مثل خود TeX حذف می‌کند.

    خطی که تمامش توضیح است کامل حذف می‌شود تا وسط پاراگراف شکست نیفتد.
    """
    out = []
    for line in text.split('\n'):
        buf, i, cut = [], 0, False
        while i < len(line):
            if line[i] == '\\' and i + 1 < len(line):
                buf.append(line[i:i + 2])
                i += 2
                continue
            if line[i] == '%':
                cut = True
                break
            buf.append(line[i])
            i += 1
        kept = ''.join(buf)
        if cut and not kept.strip():
            continue
        out.append(kept)
    return '\n'.join(out)


def read_tex(path):
    """فایل .tex را می‌خواند و includegraphics کامنت‌شده را زنده می‌کند.

    در نسخه‌ی فعلی مقاله، خط \\includegraphics کامنت است چون شکل‌ها هنوز
    ساخته نشده‌اند؛ ولی همان خط نام فایل موردنظر را نگه داشته است. اینجا
    کامنتش را برمی‌داریم تا اگر شکل بعداً ساخته شد، خودش نمایش داده شود.
    """
    src = open(path, encoding='utf-8').read()
    src = re.sub(r'(?m)^(\s*)%\s*(\\includegraphics)', r'\1\2', src)
    return strip_comments(src)


def inline_fonts(doc):
    """url("fonts/X.woff2") را با data: جایگزین می‌کند.

    کروم صفحه‌ی `file://` را «مبدأ ناشناس» می‌شمارد و بارگیری قلم از کنار
    فایل را با خطای CORS رد می‌کند؛ در آن حالت متن با قلم پیش‌فرض سیستم
    دیده می‌شود. قلمِ جاسازی‌شده به‌شکل `data:` این محدودیت را ندارد و در
    همه‌ی مرورگرها یکسان کار می‌کند. هزینه‌اش حدود ۱۳۰ کیلوبایت است.
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

    return re.sub(r'url\("([^"]+\.woff2)"\)', sub, doc), done


def image_data_uri(rel):
    """یک تصویر محلی کوچک را برای HTML تک‌فایلی به data URI تبدیل می‌کند."""
    path = os.path.join(MS, rel.replace('/', os.sep))
    if not os.path.isfile(path):
        sys.stderr.write('هشدار: تصویر سربرگ یافت نشد: %s\n' % rel)
        return ''
    ext = os.path.splitext(path)[1].lower()
    mime = 'image/png' if ext == '.png' else 'image/jpeg'
    with open(path, 'rb') as f:
        return 'data:%s;base64,%s' % (mime, base64.b64encode(f.read()).decode('ascii'))


def web_src(want):
    """(نشانی تصویر برای مرورگر، نشانی نسخه‌ی برداری) را برمی‌گرداند.

    مرورگر PDF را داخل <img> نمی‌نشاند، ولی XeLaTeX همان PDF برداری را
    می‌خواهد. پس `tools/figures_prep.py` کنار هر شکل یک PNG در
    `figures/web/` می‌سازد و اینجا اگر آن نسخه موجود بود ترجیح داده
    می‌شود. اگر نبود و خود فایل تصویر بیت‌مپ بود، همان مستقیم می‌آید.
    """
    if not want:
        return '', ''
    d, base = os.path.split(want)
    stem, ext = os.path.splitext(base)
    web = '/'.join(filter(None, (d, 'web', stem + '.png')))
    if os.path.isfile(os.path.join(MS, web.replace('/', os.sep))):
        return web, want if ext.lower() == '.pdf' else ''
    if ext.lower() != '.pdf' and os.path.isfile(
            os.path.join(MS, want.replace('/', os.sep))):
        return want, ''
    return '', ''


def take_math(text):
    """ریاضی را پیش از هر تغییری کنار می‌گذارد و شماره‌ی رابطه می‌زند."""
    def display(m):
        env, body = m.group(1), m.group(2)
        first = ''
        extra = []
        rows = []
        for row in body.split('\\\\'):
            lm = re.search(r'\\label\{([^}]+)\}', row)
            if lm:
                N['eq'] += 1
                LABELS[lm.group(1)] = str(N['eq'])
                if first:
                    extra.append(lm.group(1))
                else:
                    first = lm.group(1)
                row = row.replace(lm.group(0), '')
                row = row.rstrip() + '\\tag{%d}' % N['eq']
            rows.append(row)
        tex = '\\begin{%s}%s\\end{%s}' % (env, '\\\\'.join(rows), env)
        anchor = ' id="%s"' % html.escape(first) if first else ''
        # در align چند رابطه یک بلوک‌اند و id فقط یکی می‌تواند باشد؛ برای
        # برچسب‌های بعدی لنگر خالی می‌گذاریم تا \eqref به آن‌ها هم برسد.
        pre = ''.join('<span class="eqa" id="%s"></span>' % html.escape(k)
                      for k in extra)
        return keep_block('%s<div class="eq"%s>%s</div>' % (pre, anchor, tex))

    text = re.sub(r'\\begin\{(equation|align|gather)\}(.*?)\\end\{\1\}',
                  display, text, flags=re.S)
    # $...$ درون‌خطی
    text = re.sub(r'(?<!\\)\$(.+?)(?<!\\)\$',
                  lambda m: keep('\\(' + m.group(1) + '\\)'), text, flags=re.S)
    return text


def take_floats(text):
    """figure و table را به HTML تبدیل و کنار می‌گذارد."""
    def caption_of(body):
        cap = ''
        cm = re.search(r'\\caption\{', body)
        if cm:
            cap, end = group(body, cm.end() - 1)
            body = body[:cm.start()] + body[end:]
        lm = re.search(r'\\label\{([^}]+)\}', body)
        label = lm.group(1) if lm else ''
        if lm:
            body = body.replace(lm.group(0), '')
        return body, cap, label

    def figure(body):
        body, cap, label = caption_of(body)
        N['fig'] += 1
        num = N['fig']
        if label:
            LABELS[label] = str(num)
        # فایل شکل ممکن است در .tex کامنت شده باشد؛ هر دو حالت را می‌گیریم
        gm = re.search(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', body)
        want = gm.group(1) if gm else ''
        src, pdf = web_src(want)
        out = ['<figure id="%s">' % html.escape(label or 'fig%d' % num)]
        if src:
            img = '<img src="%s" alt="شکل %d">' % (html.escape(src), num)
            # نسخه‌ی برداری همان چیزی است که در PDF نهایی می‌نشیند؛ لینکش
            # می‌گذاریم تا با کلیک روی تصویر بتوان اصل را دید.
            if pdf:
                img = '<a href="%s" title="نسخه‌ی برداری">%s</a>' % (
                    html.escape(pdf), img)
            out.append(img)
        else:
            out.append('<div class="todo">شکل %d — <code>%s</code><br>'
                       'هنوز تولید نشده؛ بعد از اجرای شبیه‌سازی و '
                       '<code>make_figures.py</code> این اسکریپت را دوباره '
                       'اجرا کنید.</div>' % (num, html.escape(want or '؟')))
        if cap:
            out.append('<figcaption><b>شکل %d.</b> %s</figcaption>'
                       % (num, inline(cap)))
        out.append('</figure>')
        return keep_block('\n'.join(out))

    def table(body):
        body, cap, label = caption_of(body)
        N['tab'] += 1
        num = N['tab']
        if label:
            LABELS[label] = str(num)
        rows = []
        tm = re.search(r'\\begin\{tabular\}', body)
        if tm:
            inner = body[tm.end():]
            inner = inner[:inner.find('\\end{tabular}')]
            inner = re.sub(r'^\s*\{[^}]*\}', '', inner, count=1)
            inner = re.sub(r'\\(toprule|midrule|bottomrule|hline)', '', inner)
            for ri, row in enumerate([r for r in inner.split('\\\\') if r.strip()]):
                tag = 'th' if ri == 0 else 'td'
                cells = ''.join('<%s>%s</%s>' % (tag, inline(c.strip()), tag)
                                for c in row.split('&'))
                rows.append('<tr>%s</tr>' % cells)
        out = ['<figure class="tab" id="%s">'
               % html.escape(label or 'tab%d' % num)]
        if cap:
            out.append('<figcaption><b>جدول %d.</b> %s</figcaption>'
                       % (num, inline(cap)))
        out.append('<table>%s</table>' % ''.join(rows))
        out.append('</figure>')
        return keep_block('\n'.join(out))

    for env, fn in (('figure', figure), ('table', table)):
        while True:
            m = re.search(r'\\begin\{%s\}' % env, text)
            if not m:
                break
            e = re.search(r'\\end\{%s\}' % env, text[m.end():])
            if not e:
                break
            body = text[m.end():m.end() + e.start()]
            text = text[:m.start()] + fn(body) + text[m.end() + e.end():]
    return text


def inline(text):
    """دستورهای درون‌خطیِ به‌کاررفته در همین مقاله."""
    text = text.replace('<', '&lt;').replace('>', '&gt;')

    def cite(m):
        note = (m.group(1) or '').strip()
        out = []
        for k in [k.strip() for k in m.group(2).split(',') if k.strip()]:
            out.append('<a href="#ref-%s">%d</a>'
                       % (html.escape(k), CITES.setdefault(k, len(CITES) + 1)))
        body = ', '.join(out)
        if note:                      # \cite[pp.~34--37]{key} → [3, pp. 34–37]
            body += ', ' + note
        return '<sup>[%s]</sup>' % body

    text = re.sub(r'\\cite(?:\[([^\]]*)\])?\{([^}]*)\}', cite, text)
    # ارجاع‌ها در پایان و پس از شناخته‌شدن همه‌ی برچسب‌ها جایگزین می‌شوند
    text = re.sub(r'\\eqref\{([^}]+)\}', r'<x-ref k="\1" p="1"></x-ref>', text)
    text = re.sub(r'\\ref\{([^}]+)\}', r'<x-ref k="\1"></x-ref>', text)

    for cmd, tag in (('textbf', 'b'), ('emph', 'i'), ('textit', 'i'),
                     ('texttt', 'code')):
        while True:
            m = re.search(r'\\%s\{' % cmd, text)
            if not m:
                break
            arg, end = group(text, m.end() - 1)
            text = text[:m.start()] + '<%s>%s</%s>' % (tag, arg, tag) + text[end:]

    text = (text.replace('~', '\u00a0').replace('\\,', '\u202f')
                .replace('\\%', '%').replace('\\&', '&').replace('\\_', '_')
                .replace('---', '\u2014').replace('--', '\u2013'))
    for junk in ('\\noindent', '\\centering', '\\bigskip', '\\medskip',
                 '\\maketitle', '\\newpage', '\\clearpage'):
        text = text.replace(junk, '')
    return text


def bib(path):
    """خواننده‌ی ساده‌ی BibTeX: نویسنده، عنوان، مجله، سال، DOI."""
    if not os.path.isfile(path):
        return {}
    src = open(path, encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'@\w+\s*\{\s*([^,\s]+)\s*,', src):
        body, _ = group(src, src.index('{', m.start()))
        f = {}
        for fm in re.finditer(r'(\w+)\s*=\s*', body):
            j = fm.end()
            if j < len(body) and body[j] == '{':
                val, _ = group(body, j)
            elif j < len(body) and body[j] == '"':
                val = body[j + 1:body.index('"', j + 1)]
            else:
                k = body.find(',', j)
                val = body[j:k if k != -1 else len(body)]
            f[fm.group(1).lower()] = ' '.join(val.replace('{', '')
                                              .replace('}', '').split())
        out[m.group(1)] = f
    return out


def ref_line(f):
    au = [a.strip() for a in re.split(r'\s+and\s+', f.get('author', ''))
          if a.strip()]
    names = []
    for a in au[:6]:
        if ',' in a:
            last, first = a.split(',', 1)
            names.append('%s %s' % (last.strip(),
                                    ' '.join(p[0] + '.' for p in first.split())))
        else:
            names.append(a)
    if len(au) > 6:
        names.append('et al.')
    bits = [html.escape(', '.join(names)),
            html.escape(f.get('title', '').replace('--', '\u2013'))]
    venue = f.get('journal') or f.get('booktitle') or f.get('publisher') or ''
    if venue:
        v = '<i>%s</i>' % html.escape(venue)
        if f.get('volume'):
            v += ' <b>%s</b>' % html.escape(f['volume'])
        if f.get('pages'):
            v += ', ' + html.escape(f['pages'].replace('--', '\u2013'))
        bits.append(v)
    if f.get('year'):
        bits.append('(%s)' % html.escape(f['year']))
    # نقطه‌ی تکراری بعد از حروف اختصاری نویسنده حذف می‌شود
    line = '. '.join(b.rstrip('.') for b in bits if b) + '.'
    if f.get('doi'):
        line += ' <a href="https://doi.org/%s">doi:%s</a>' % (f['doi'], f['doi'])
    return line


def body_html(text, number=False):
    """عنوان‌ها را شماره‌گذاری و بقیه را به پاراگراف تبدیل می‌کند.

    با ``number=True`` هر پاراگراف یک شماره‌ی حاشیه‌ای می‌گیرد تا داور
    بتواند در بازخوردش به «پاراگراف ۱۲» ارجاع دهد.
    """
    pieces, pos = [], 0
    pat = re.compile(r'\\(section|subsection)\*?\{')
    while True:
        m = pat.search(text, pos)
        if not m:
            pieces.append(text[pos:])
            break
        pieces.append(text[pos:m.start()])
        title, after = group(text, m.end() - 1)
        lm = re.match(r'\s*\\label\{([^}]+)\}', text[after:after + 200])
        label = lm.group(1) if lm else ''
        if m.group(1) == 'section':
            N['sec'] += 1
            N['sub'] = 0
            num, tag = str(N['sec']), 'h2'
        else:
            N['sub'] += 1
            num, tag = '%d.%d' % (N['sec'], N['sub']), 'h3'
        anchor = label or 'sec' + num.replace('.', '-')
        if label:
            LABELS[label] = num
        head = inline(' '.join(title.split()))
        TOC.append((tag, num, head, anchor))
        pieces.append('\n\n' + keep('<%s id="%s"><span class="n">%s</span> %s'
                                    '</%s>' % (tag, html.escape(anchor), num,
                                               head, tag)) + '\n\n')
        pos = after + (lm.end() if lm else 0)
    text = ''.join(pieces)

    out = []
    for block in re.split(r'\n\s*\n', text):
        block = block.strip()
        if not block:
            continue
        if re.fullmatch(r'\x00\d+\x00', block):     # عنوان/شکل/جدول/رابطه
            out.append(block)
        elif number:
            N['par'] += 1
            out.append('<p id="p%d"><a class="pn" href="#p%d">%d</a>%s</p>'
                       % (N['par'], N['par'], N['par'],
                          inline(re.sub(r'\s+', ' ', block))))
        else:
            out.append('<p>%s</p>' % inline(re.sub(r'\s+', ' ', block)))
    return '\n'.join(out)


PAGE = """<!DOCTYPE html>
<html lang="fa" dir="rtl"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>@@T@@</title>
<style>
/* قلم متن: وزیرمتن (SIL OFL 1.1). فایل .woff2 آن در manuscript/fonts کنار
   همین فایل است، ولی نشانی زیر پیش از نوشتن خروجی به data: تبدیل می‌شود
   (inline_fonts) تا کروم هم در file:// قلم را نشان دهد، نه فقط فایرفاکس. */
@font-face{font-family:"Vazirmatn";src:url("fonts/Vazirmatn-Regular.woff2")
 format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:"Vazirmatn";src:url("fonts/Vazirmatn-Bold.woff2")
 format("woff2");font-weight:700;font-display:swap}
:root{--ink:#182230;--soft:#5d6877;--line:#d9e0e8;--tint:#f5f8fb;
 --accent:#123f70;--accent2:#8b6a24;--num:#8a1c1c;--maxw:49rem}
*{box-sizing:border-box}
html{background:#e9edf2;scroll-behavior:smooth}
body{font-family:"Vazirmatn","XB Niloofar","Tahoma",sans-serif;
 font-size:1.02rem;line-height:2.05;max-width:var(--maxw);margin:2.5rem auto;
 padding:2.4rem 3.3rem;text-align:justify;text-justify:inter-word;color:var(--ink);
 background:#fff;box-shadow:0 12px 40px #23364d22;-webkit-font-smoothing:antialiased;
 overflow-wrap:break-word;word-wrap:break-word}
p,li,figcaption,td,th{overflow-wrap:anywhere;word-break:normal}
img,svg,table{max-width:100%}
mjx-container{max-width:100%;font-weight:400!important;color:#263445}
mjx-container[jax="SVG"][display="true"]{width:100%;overflow-x:auto;overflow-y:hidden;
 font-size:.94em!important}
mjx-container[jax="SVG"][display="true"] svg{max-width:100%!important;height:auto!important}
.article-head{border-top:7px solid var(--accent);padding-top:1.25rem;margin-bottom:1.45rem}
.brand{display:flex;align-items:center;justify-content:space-between;gap:1rem;
 padding-bottom:.85rem;border-bottom:1px solid var(--line);color:var(--accent)}
.brand-logo{width:4.2rem;height:4.2rem;object-fit:contain;display:block;
 filter:drop-shadow(0 2px 3px #123f7022)}
.brand-name{font-size:1.08rem;font-weight:700}.brand-type{color:var(--soft);font-size:.78rem}
h1{font-size:1.62rem;line-height:1.85;text-align:center;font-weight:700;
 letter-spacing:-.01em;margin:1.35rem auto 1rem;max-width:44rem}
.byline{text-align:center;font-size:1.02rem;font-weight:700;color:var(--accent);margin:.4rem 0}
.affiliation{text-align:center;color:var(--soft);font-size:.92rem;line-height:1.85}
.paper-date{display:inline-block;margin-top:.35rem;padding:.1rem .7rem;border-radius:999px;
 background:var(--tint);border:1px solid var(--line);color:var(--soft);font-size:.82rem}
.print-tools{position:fixed;direction:rtl;left:1rem;bottom:1rem;z-index:10;
 display:flex;gap:.5rem;align-items:center;background:#fff;padding:.55rem;border-radius:10px;
 box-shadow:0 4px 20px #12263a33;border:1px solid var(--line)}
.print-tools button{font:inherit;border:0;border-radius:7px;background:var(--accent);color:#fff;
 padding:.55rem .9rem;cursor:pointer}.print-tools span{font-size:.74rem;color:var(--soft);max-width:11rem}
h2{font-size:1.22rem;line-height:1.8;font-weight:700;margin:2.6rem 0 .9rem;
 padding-bottom:.35rem;border-bottom:2px solid var(--line)}
h3{font-size:1.06rem;line-height:1.8;font-weight:700;margin:1.9rem 0 .6rem;
 color:#22262e}
p{margin:0 0 .85rem}
/* شماره‌ی حاشیه‌ای پاراگراف: برای اینکه داور بتواند بنویسد «پاراگراف ۱۴».
   بیرون از ستون متن می‌نشیند و در چاپ حذف می‌شود. */
p[id^="p"]{position:relative}
a.pn{position:absolute;inset-inline-start:-2.6rem;top:.45rem;
 font-size:.72rem;line-height:1;color:#b9c0ca;text-decoration:none;
 direction:ltr;user-select:none;font-family:"Times New Roman",serif}
a.pn:hover{color:var(--accent)}
p[id^="p"]:target{background:#fff3b0;border-radius:3px}
a{color:var(--accent)}
h2 .n,h3 .n{color:var(--num);font-weight:700;margin-inline-end:.35rem}
.abs{background:var(--tint);border:1px solid var(--line);border-radius:8px;
 padding:1.1rem 1.35rem;font-size:.97rem;line-height:1.95}
.abs h2{border:0;margin:0 0 .6rem;padding:0;font-size:1.02rem;
 text-align:center;letter-spacing:.02em}
.kw{font-size:.92rem;color:var(--soft);line-height:1.9;margin:.9rem 0 1.6rem}
.kw b{color:var(--ink)}
.toc{border:1px solid var(--line);border-radius:8px;padding:.9rem 1.35rem;
 font-size:.94rem;line-height:1.9;background:#fff}
.toc>b{display:block;margin-bottom:.4rem}
.toc a{color:var(--accent);text-decoration:none}
.toc a:hover{text-decoration:underline}
.toc div{margin:.12rem 0}
.toc .m>a{font-weight:700}
.toc .s{padding-inline-start:1.5rem;font-size:.9rem}
.toc .n{color:var(--num);display:inline-block;min-width:2.1rem}
.eq{margin:1.3rem 0;padding:.2rem 0;overflow-x:auto;direction:ltr;
 text-align:center}
figure{margin:2rem 0;text-align:center}
figure img{max-width:100%;height:auto;border:1px solid var(--line);
 border-radius:6px;background:#fff;padding:.35rem}
figure a{display:inline-block;line-height:0}
figcaption{font-size:.9rem;line-height:1.85;color:var(--soft);
 margin-top:.7rem;text-align:justify}
figcaption b{color:var(--ink)}
figure.tab figcaption{margin:0 0 .6rem}
.todo{border:1px dashed #c9b98a;background:#fff8e6;color:#7a5b10;
 border-radius:6px;padding:1.4rem 1rem;font-size:.9rem;line-height:1.9}
table{border-collapse:collapse;margin:.5rem auto;font-size:.94rem;
 line-height:1.75}
th,td{padding:.45rem 1rem;text-align:right;border-bottom:1px solid var(--line)}
th{background:var(--tint);border-top:1.6px solid #333;
 border-bottom:1.2px solid #333;font-weight:700}
tr:last-child td{border-bottom:1.6px solid #333}
sup a{text-decoration:none;padding:0 .1rem}
ol.refs{padding-inline-start:1.6rem}
ol.refs li{direction:ltr;text-align:left;font-family:"Times New Roman",serif;
 font-size:.9rem;line-height:1.75;margin:.5rem 0}
/* کادر راهنما در بالای صفحه: فقط برای نسخه‌ی بازبینی */
.hint{border:1px solid var(--line);border-inline-start:4px solid var(--accent);
 background:var(--tint);border-radius:8px;padding:.85rem 1.1rem;
 font-size:.9rem;line-height:1.9;color:var(--soft);margin:0 0 1.6rem}
.hint b{color:var(--ink)}
.hint code{font-size:.85em}
:target{background:#fff3b0;border-radius:3px}
code{direction:ltr;display:inline-block;font-size:.9em;
 background:var(--tint);border:1px solid var(--line);border-radius:4px;
 padding:0 .3em}
@media (max-width:40rem){html{background:#fff}body{font-size:.98rem;line-height:1.95;
 margin:0 auto;padding:1.2rem;box-shadow:none}h1{font-size:1.3rem}.brand-logo{width:3.4rem;height:3.4rem}
 a.pn{display:none}.print-tools span{display:none}}
@page{size:A4;margin:18mm 20mm 20mm 20mm}
@media print{
 html,body{background:#fff;width:auto!important;min-width:0!important;max-width:100%!important;
  margin:0!important;padding:0!important;overflow:visible!important}
 body{font-size:10.25pt;line-height:1.78;box-shadow:none;color:#111;text-align:justify}
 main,header,nav,section,article,div,p,ol,li,figure,figcaption{min-width:0;max-width:100%}
 .brand{width:100%}.brand-logo{width:17mm;height:17mm}
 .eq{width:100%;max-width:100%;overflow:hidden;font-size:9.2pt}
 mjx-container{font-weight:400!important;color:#182230!important}
 mjx-container[jax="SVG"][display="true"]{font-size:.88em!important;overflow:hidden!important}
 mjx-container[jax="SVG"][display="true"] svg{max-width:100%!important;height:auto!important}
 table{width:100%;max-width:100%;table-layout:fixed}
 th,td{padding:1.5mm 2mm}
 ol.refs{max-width:100%;padding-inline-start:6mm}
 ol.refs li,ol.refs a{overflow-wrap:anywhere;word-break:break-word}
 .article-head{border-top:5px solid var(--accent);margin-bottom:8mm}
 h1{font-size:17pt;line-height:1.65;margin:7mm auto 4mm}
 h2{font-size:13pt;margin-top:8mm;break-after:avoid-page;page-break-after:avoid}
 h3{font-size:11.5pt;margin-top:6mm;break-after:avoid-page;page-break-after:avoid}
 p{orphans:3;widows:3;margin-bottom:2.5mm}
 .abs{break-inside:avoid-page;border-radius:0;background:#f5f7f9}
 .toc{break-before:page;page-break-before:always;border-radius:0}
 figure,.eq,table{break-inside:avoid-page;page-break-inside:avoid}
 figure{margin:6mm 0}figure img{border:0;padding:0;border-radius:0}
 figcaption{font-size:9pt;line-height:1.65}
 ol.refs li{font-size:8.8pt;line-height:1.5;break-inside:avoid}
 a{color:inherit;text-decoration:none}
 a.pn,.hint,.print-tools{display:none!important}
 *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
</style>
<script>
window.MathJax={tex:{inlineMath:[['\\\\(','\\\\)']],tags:'none',
 macros:{Fp:'F_p',nm:['#1\\\\,\\\\text{nm}',1]}},options:{enableMenu:false}};
</script>
<script defer src="@@MJ@@"></script>
</head><body>
<div class="print-tools"><button type="button" onclick="window.print()">ذخیره به صورت PDF</button>
<span>در پنجره چاپ: A4، مقیاس ۱۰۰٪ و Background graphics روشن باشد.</span></div>
<header class="article-head">
 <div class="brand"><div><div class="brand-name">@@AFF@@</div>
 <div class="brand-type">مقاله علمی ـ پژوهشی دانشجویی</div></div>
 <img class="brand-logo" src="assets/university-isfahan-logo.png" alt="نشان دانشگاه اصفهان"></div>
 <h1>@@T@@</h1>
 <div class="byline">@@AU@@</div>
 <div class="affiliation">@@AFF@@<br>استاد راهنما: @@ADV@@<br>
 <span class="paper-date">@@DATE@@</span></div>
</header>
<div class="hint"><b>نسخه آماده چاپ تک‌ستونه.</b>
برای خروجی PDF از دکمه پایین صفحه استفاده کنید. شماره‌های خاکستری کنار
پاراگراف‌ها فقط در نمایشگر دیده می‌شوند و در چاپ حذف خواهند شد.</div>
<div class="abs"><h2>چکیده</h2>@@ABS@@</div>
<p class="kw"><b>کلیدواژه‌ها:</b> @@KW@@</p>
<nav class="toc"><b>فهرست</b>@@TOC@@</nav>
@@BODY@@
<h2 id="refs">مراجع</h2>
<ol class="refs">@@REFS@@</ol>
</body></html>
"""


def main():
    main_tex = read_tex(os.path.join(MS, 'main.tex'))

    def command_value(name, default=''):
        m = re.search(r'\\(?:newcommand\{\\' + re.escape(name) + r'\}|'
                      + re.escape(name) + r')\{', main_tex)
        return ' '.join(group(main_tex, m.end() - 1)[0].split()) if m else default

    tm = re.search(r'\\title\{', main_tex)
    title = ' '.join(group(main_tex, tm.end() - 1)[0].split()) if tm else ''
    authors = command_value('paperauthors', 'امین حسین سدیدی، پارسا مولایی')
    affiliation = command_value('paperaffiliation', 'دانشگاه اصفهان')
    advisor = command_value('paperadvisor', 'دکتر مالک باقری هارونی')
    paperdate = command_value('paperdate', 'مهر ۱۴۰۵')

    am = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', main_tex, re.S)
    abstract = am.group(1) if am else ''

    tail = main_tex[am.end():] if am else ''
    km = re.search(r'\\textbf\{کلمات کلیدی:\}(.*?)\n\s*\n', tail, re.S)
    keywords = km.group(1) if km else ''

    src = []
    for rel in re.findall(r'\\input\{([^}]+)\}', main_tex):
        p = os.path.join(MS, rel.replace('/', os.sep))
        if not p.endswith('.tex'):
            p += '.tex'
        if os.path.isfile(p):
            src.append(read_tex(p))
        else:
            sys.stderr.write('هشدار: فایل یافت نشد %s\n' % p)

    # ترتیب مهم است: ریاضی، سپس شکل/جدول، سپس عنوان و پاراگراف
    abs_html = body_html(take_math(abstract))
    kw_html = inline(' '.join(take_math(keywords).split()))
    text = take_floats(take_math('\n\n'.join(src)))
    main_html = body_html(text, number=True)

    toc = '\n'.join('<div class="%s"><a href="#%s"><span class="n">%s</span> %s'
                    '</a></div>' % ('s' if tag == 'h3' else 'm',
                                    html.escape(a), num, t)
                    for tag, num, t, a in TOC)

    entries = bib(os.path.join(MS, 'references.bib'))
    refs = []
    for key, _ in sorted(CITES.items(), key=lambda kv: kv[1]):
        if key in entries:
            refs.append('<li id="ref-%s">%s</li>'
                        % (html.escape(key), ref_line(entries[key])))
        else:
            sys.stderr.write('هشدار: کلید در references.bib نیست: %s\n' % key)
            refs.append('<li id="ref-%s"><i>missing: %s</i></li>'
                        % (html.escape(key), html.escape(key)))

    doc = PAGE
    if os.path.isfile(os.path.join(MS, MATHJAX_LOCAL)):
        mj = MATHJAX_LOCAL.replace(os.sep, '/')
        print('MathJax: نسخه‌ی محلی %s' % mj)
    else:
        mj = MATHJAX_CDN
        print('MathJax: از CDN (برای نسخه‌ی آفلاین:'
              ' python tools/vendor_mathjax.py)')
    for k, v in (('@@T@@', inline(title)),
                 ('@@AU@@', inline(authors)), ('@@AFF@@', inline(affiliation)),
                 ('@@ADV@@', inline(advisor)),
                 ('@@DATE@@', inline(paperdate)), ('@@ABS@@', abs_html),
                 ('@@KW@@', kw_html), ('@@TOC@@', toc),
                 ('@@BODY@@', main_html), ('@@REFS@@', '\n'.join(refs)),
                 ('@@MJ@@', mj)):
        doc = doc.replace(k, v)
    doc = unkeep(doc)

    # ارجاع‌ها را حالا که همه‌ی برچسب‌ها شناخته شده‌اند جایگزین کن
    def xref(m):
        key, paren = m.group(1), bool(m.group(2))
        num = LABELS.get(key)
        if num is None:
            sys.stderr.write('هشدار: برچسب ناشناخته %s\n' % key)
            return '<b style="color:#b00">؟؟</b>'
        return '<a href="#%s">%s</a>' % (html.escape(key),
                                         '(%s)' % num if paren else num)

    doc = re.sub(r'<x-ref k="([^"]+)"( p="1")?></x-ref>', xref, doc)

    # قلم را داخل خود HTML جاسازی کن (دلیل: توضیح inline_fonts)
    doc, fonts = inline_fonts(doc)
    if fonts:
        print('قلمِ جاسازی‌شده: %s' % ', '.join(fonts))
    else:
        sys.stderr.write('هشدار: هیچ قلمی جاسازی نشد؛ متن با قلم پیش‌فرض'
                         ' سیستم دیده می‌شود.\n')

    open(OUT, 'w', encoding='utf-8', newline='\n').write(doc)

    # نسخه ریشه برای Live Preview باید سبک بماند. بعضی proxy/viewerها پیش
    # از رسیدن parser به <body> روی CSS دارای Base64 بزرگ متوقف می‌شوند و
    # صفحه‌ای کاملاً سفید نشان می‌دهند. در preview.html قلم همچنان جاسازی
    # است، اما در index.html از فایل‌های محلی هم‌مبدأ استفاده می‌کنیم.
    root_doc = doc
    font_paths = iter(('manuscript/fonts/Vazirmatn-Regular.woff2',
                       'manuscript/fonts/Vazirmatn-Bold.woff2'))
    root_doc = re.sub(r'data:font/woff2;base64,[A-Za-z0-9+/=]+',
                      lambda _m: next(font_paths), root_doc, count=2)
    # دارایی‌های MathJax، شکل و لوگو زیر manuscript/ هستند. از <base> عمداً
    # استفاده نمی‌شود، چون anchorهای داخلی را هم منحرف می‌کند.
    root_doc = re.sub(r'((?:src|href)=")((?:vendor|figures|assets)/)',
                      r'\1manuscript/\2', root_doc)
    open(ROOT_OUT, 'w', encoding='utf-8', newline='\n').write(root_doc)

    print('نوشته شد: %s  (%d کیلوبایت)'
          % (OUT, len(doc.encode('utf-8')) // 1024))
    print('نسخه‌ی ریشه: %s (دارایی‌ها از manuscript/ بارگیری می‌شوند)'
          % ROOT_OUT)
    print('بخش‌ها: %d | شکل: %d | جدول: %d | رابطه: %d | مرجع: %d'
          % (N['sec'], N['fig'], N['tab'], N['eq'], len(refs)))
    left = sorted(set(re.findall(r'\\([a-zA-Z]+)', re.sub(
        r'<script.*?</script>|<div class="eq".*?</div>|\\\(.*?\\\)',
        '', doc, flags=re.S))))
    print('دستورهای لاتک ترجمه‌نشده بیرون از ریاضی: %s'
          % (', '.join('\\' + x for x in left) if left else 'ندارد'))
    return 1 if '\x00' in doc else 0


if __name__ == '__main__':
    raise SystemExit(main())

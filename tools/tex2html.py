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
OUT = os.path.join(MS, 'final.html' if '--final' in sys.argv else 'preview.html')

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


def inline_images(doc):
    """تصویرهای شکل‌ها را به data: تبدیل می‌کند.

    دلیل: پیش‌نمایش و نسخه‌ی نهایی باید تک‌فایلِ خودبسنده باشند تا در
    نمایشگر تک‌فایلی، در zip بازبینی و در `file://` بدون هیچ منبع بیرونی
    کامل دیده شوند؛ وگرنه شکل‌ها قاب شکسته می‌شوند.
    """
    done = []

    def sub(m):
        rel = m.group(1)
        path = os.path.join(MS, rel.replace('/', os.sep))
        if not os.path.isfile(path):
            sys.stderr.write('هشدار: تصویر یافت نشد: %s\n' % rel)
            return m.group(0)
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('ascii')
        done.append(rel)
        return 'src="data:image/png;base64,%s"' % b64

    return re.sub(r'src="(figures/web/[^"]+)"', sub, doc), done


def inline_mathjax(doc):
    """کد MathJax محلی را داخل خود HTML می‌گذارد (خودبسندگی، مثل قلم و شکل).

    برچسب <script defer src> فقط وقتی معنا دارد که فایل کنار صفحه قابل
    دسترس باشد؛ در نمایشگر تک‌فایلی نیست. پس وقتی نسخه‌ی محلی موجود است،
    کل bundle را درون‌خطی می‌کنیم.
    """
    rel = MATHJAX_LOCAL.replace(os.sep, '/')
    tag = '<script defer src="%s"></script>' % rel
    if tag not in doc:
        return doc, False
    path = os.path.join(MS, MATHJAX_LOCAL)
    if not os.path.isfile(path):
        return doc, False
    js = open(path, encoding='utf-8').read()
    if '</script' in js.lower():
        sys.stderr.write('هشدار: MathJax رشته‌ی </script دارد؛ درون‌خطی نشد.\n')
        return doc, False
    return doc.replace(tag, '<script>/* mathjax-inline */\n%s\n</script>' % js), True


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
        tex = tex.replace('<', '&lt;').replace('>', '&gt;')   # HTML-safe
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
                  lambda m: keep('\\(' + m.group(1).replace('<', '&lt;').replace('>', '&gt;') + '\\)'),
                  text, flags=re.S)
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
            inner = inner.lstrip()
            if inner.startswith('{'):           # مشخصه‌ی ستون‌ها، حتی با p{..\linewidth} تودرتو
                _, k = group(inner, 0)
                inner = inner[k:]
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
        # محفظه‌ی اسکرول: جدول‌های پهن (مثل خلاصه‌ی حالت‌ها) در ستون باریک
        # یا ورق A4 از چپ و راست بیرون نمی‌زنند؛ داخل خود جدول اسکرول می‌شود.
        out.append('<div class="tblwrap"><table>%s</table></div>'
                   % ''.join(rows))
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

    # \paragraph{عنوان} → عنوان درشت درون‌خطی ؛ \footnote{...} → پرانتز
    for cmd, tag in (('paragraph', 'b class="para"'), ('footnote', 'span class="fn"')):
        while True:
            m = re.search(r'\\%s\{' % cmd, text)
            if not m:
                break
            arg, end = group(text, m.end() - 1)
            close = tag.split()[0]
            if cmd == 'footnote':
                rep = ' <%s>(%s)</%s>' % (tag, arg, close)
            else:
                rep = '<%s>%s</%s> ' % (tag, arg, close)
            text = text[:m.start()] + rep + text[end:]

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
                 '\\maketitle', '\\newpage', '\\clearpage', '\\appendix',
                 '\\tableofcontents'):
        text = text.replace(junk, '')
    # \addcontentsline فقط برای فهرستِ خروجی LaTeX است؛ در HTML فهرست خودمان
    # را داریم، پس آن را دور می‌اندازیم.
    text = re.sub(r'\\addcontentsline\{[^}]*\}\{[^}]*\}\{[^}]*\}', '', text)
    return text


def bib(path):
    """خواننده‌ی ساده‌ی BibTeX: نویسنده، عنوان، مجله، سال، DOI."""
    if not os.path.isfile(path):
        return {}
    src = open(path, encoding='utf-8').read()
    for a, b in (('{\\"u}', 'ü'), ('{\\"o}', 'ö'), ('{\\"a}', 'ä'), ('{\\aa}', 'å'),
                 ('\\"u', 'ü'), ('\\"o', 'ö'), ('\\"a', 'ä'), ('\\aa ', 'å'),
                 ("\\'e", 'é'), ('\\&', '&')):
        src = src.replace(a, b)
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
    pat = re.compile(r'\\(section|subsection)(\*?)\{')
    while True:
        m = pat.search(text, pos)
        if not m:
            pieces.append(text[pos:])
            break
        pieces.append(text[pos:m.start()])
        title, after = group(text, m.end() - 1)
        lm = re.match(r'\s*\\label\{([^}]+)\}', text[after:after + 200])
        label = lm.group(1) if lm else ''
        starred = m.group(2) == '*'
        if m.group(1) == 'section':
            if not starred:
                N['sec'] += 1
            N['sub'] = 0
            num, tag = ('' if starred else str(N['sec'])), 'h2'
        else:
            if not starred:
                N['sub'] += 1
            num, tag = ('' if starred else '%d.%d' % (N['sec'], N['sub'])), 'h3'
        anchor = label or 'sec' + num.replace('.', '-') or 'sec-u%d' % len(TOC)
        if label:
            LABELS[label] = num
        head = inline(' '.join(title.split()))
        TOC.append((tag, num, head, anchor))
        pieces.append('\n\n' + keep('<%s id="%s">%s%s</%s>'
                                    % (tag, html.escape(anchor),
                                       ('<span class="n">%s</span> ' % num)
                                       if num else '',
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
<html lang="fa" dir="rtl" class="@@CLS@@"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>@@T@@</title>
<style>
@font-face{font-family:"Vazirmatn";src:url("fonts/Vazirmatn-Regular.woff2") format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:"Vazirmatn";src:url("fonts/Vazirmatn-Bold.woff2") format("woff2");font-weight:700;font-display:swap}
:root{--ink:#16181d;--soft:#5b6472;--line:#e3e6ea;--tint:#f6f8fa;
 --accent:#0b4fa0;--num:#8a1c1c;--maxw:46rem}
*{box-sizing:border-box}
html{overflow-x:clip}
body{font-family:"Vazirmatn","XB Niloofar","Tahoma",sans-serif;
 font-size:1.02rem;line-height:2.05;max-width:var(--maxw);margin:2.5rem auto;
 padding:0 1.35rem;padding-inline-start:2.9rem;text-align:justify;
 text-justify:inter-word;color:var(--ink);background:#fff;
 -webkit-font-smoothing:antialiased;overflow-x:clip}
h1{font-size:1.5rem;line-height:1.9;text-align:center;font-weight:700;
 margin:0 0 1.2rem}
h2{font-size:1.2rem;line-height:1.8;font-weight:700;margin:2.6rem 0 .9rem;
 padding-bottom:.35rem;border-bottom:2px solid var(--line)}
h3{font-size:1.06rem;line-height:1.8;font-weight:700;margin:1.9rem 0 .6rem;
 color:#22262e}
p{margin:0 0 .85rem}
p[id^="p"]{position:relative}
a.pn{position:absolute;inset-inline-start:-2.35rem;top:.45rem;font-size:.72rem;
 line-height:1;color:#b9c0ca;text-decoration:none;direction:ltr;
 user-select:none;font-family:"Times New Roman",serif}
a.pn:hover{color:var(--accent)}
p[id^="p"]:target{background:#fff3b0;border-radius:3px}
a{color:var(--accent)}
h2 .n,h3 .n{color:var(--num);font-weight:700;margin-inline-end:.35rem}
/* --- صفحه‌ی اول (جلد) --- */
.cover{border:1px solid #222;padding:2.4rem 1.7rem;margin:0 0 2.6rem;
 text-align:center;display:flex;flex-direction:column;
 justify-content:space-between;gap:2rem;min-height:34rem}
.cover-top{font-size:1.05rem;font-weight:700;line-height:2.2;
 border-bottom:2px solid #222;padding-bottom:1rem}
.cover-top small{display:block;font-weight:400;font-size:.88rem;
 color:var(--soft)}
.cover-title{font-size:1.32rem;font-weight:700;line-height:2.15;margin:auto 0}
.cover-authors{font-size:1.05rem;line-height:2.2;font-weight:700}
.cover-authors small{display:block;font-weight:400;font-size:.88rem;
 color:var(--soft)}
.cover-advisor{font-size:.98rem;line-height:2;margin-top:.7rem}
.cover-bottom{font-size:.9rem;color:var(--soft);line-height:2;
 border-top:1px solid var(--line);padding-top:1rem}
.maintitle,.byline{display:none}
.byline{text-align:center;margin:0 0 1.8rem}
.byline p{margin:0;text-align:center}
.authors{font-size:1.06rem;font-weight:700;line-height:2.1}
.advisor{font-size:.98rem;font-weight:700;margin-top:.8rem !important;
 line-height:2}
.affil{font-size:.86rem;color:var(--soft);line-height:1.8}
.abs{background:var(--tint);border:1px solid var(--line);border-radius:4px;
 padding:1.1rem 1.35rem;font-size:.97rem;line-height:1.95}
.abs h2{border:0;margin:0 0 .6rem;padding:0;font-size:1.02rem;
 text-align:center;letter-spacing:.02em}
.kw{font-size:.92rem;color:var(--soft);line-height:1.9;margin:.9rem 0 1.6rem;
 text-align:center}
.kw b{color:var(--ink)}
.toc{border:1px solid var(--line);border-radius:4px;padding:.9rem 1.35rem;
 font-size:.94rem;line-height:1.9;background:#fff}
.toc>b{display:block;margin-bottom:.4rem}
.toc a{color:var(--accent);text-decoration:none}
.toc a:hover{text-decoration:underline}
.toc div{margin:.12rem 0}
.toc .m>a{font-weight:700}
.toc .s{padding-inline-start:1.5rem;font-size:.9rem}
.toc .n{color:var(--num);display:inline-block;min-width:2.1rem}
.eq{margin:1.3rem 0;padding:.2rem 0;overflow-x:auto;direction:ltr;
 text-align:center;max-width:100%}
mjx-container[display="true"]{max-width:100%;overflow-x:auto}
figure{margin:2rem 0;text-align:center}
figure img{max-width:100%;height:auto;border:1px solid var(--line);
 border-radius:3px;background:#fff;padding:.35rem}
figure a{display:inline-block;line-height:0}
figcaption{font-size:.9rem;line-height:1.85;color:var(--soft);
 margin-top:.7rem;text-align:justify}
figcaption b{color:var(--ink)}
figure.tab figcaption{margin:0 0 .6rem;text-align:center}
.todo{border:1px dashed #c9b98a;background:#fff8e6;color:#7a5b10;
 border-radius:4px;padding:1.4rem 1rem;font-size:.9rem;line-height:1.9}
.tblwrap{overflow-x:auto;max-width:100%;margin:1rem 0}
table{border-collapse:collapse;margin:.5rem auto;font-size:.94rem;
 line-height:1.75}
th,td{padding:.45rem 1rem;text-align:right;border-bottom:1px solid var(--line)}
th{background:none;border-top:1.6px solid #333;border-bottom:1.2px solid #333;
 font-weight:700}
tr:last-child td{border-bottom:1.6px solid #333}
sup a{text-decoration:none;padding:0 .1rem}
ol.refs{padding-inline-start:1.6rem}
ol.refs li{direction:ltr;text-align:left;font-family:"Times New Roman",serif;
 font-size:.9rem;line-height:1.75;margin:.5rem 0;overflow-wrap:anywhere}
.hint{border:1px solid var(--line);border-inline-start:4px solid var(--accent);
 background:var(--tint);border-radius:4px;padding:.85rem 1.1rem;font-size:.9rem;
 line-height:1.9;color:var(--soft);margin:0 0 1.6rem}
.hint b{color:var(--ink)}
.hint code{font-size:.85em}
:target{background:#fff3b0;border-radius:3px}
code{direction:ltr;display:inline-block;font-size:.9em;background:var(--tint);
 border:1px solid var(--line);border-radius:3px;padding:0 .3em}
.fn{font-size:.85em;color:#555} b.para{color:#7a1f1f}
@media (max-width:34rem){body{font-size:.98rem;line-height:1.95;
 margin:1.2rem auto;padding-inline-start:1.1rem}h1{font-size:1.3rem}
 a.pn{display:none}.cover{min-height:0;gap:1.4rem;padding:1.6rem 1rem}}
/* نسخه‌ی نهایی: ورق A4 */
html.final,body.final{background:#e6e8eb;max-width:none !important;
 margin:0 !important;padding:0 !important;width:100%}
body.final .sheet{box-sizing:border-box;background:#fff;width:210mm;
 max-width:calc(100% - 2rem);margin:2rem auto 4rem;padding:24mm 22mm 28mm;
 box-shadow:0 2px 18px rgba(0,0,0,.14)}
body.final .sheet>*{max-width:100%}
body.final a.pn,body.final .hint,body.final .toc{display:none}
body.final h1{margin-top:0;font-size:1.42rem;line-height:1.9}
body.final .abs{background:#fff;border:0;border-top:1.6px solid #333;
 border-bottom:1.6px solid #333;border-radius:0;padding:1rem .2rem}
body.final .abs h2{text-align:right;font-size:1rem}
body.final .kw{text-align:right}
body.final figure img{border:0;padding:0}
body.final figcaption{text-align:justify}
body.final .cover{margin-bottom:2.2rem}
body.final .foot{margin-top:3rem;border-top:1px solid var(--line);
 padding-top:.6rem;font-size:.82rem;color:var(--soft);text-align:center}
body.final .pdfbar{position:fixed;top:14px;left:14px;z-index:9;direction:rtl}
body.final .pdfbar button{font-family:inherit;font-size:.95rem;font-weight:700;
 color:#fff;background:var(--accent);border:0;border-radius:6px;
 padding:.55rem 1.1rem;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.2)}
body.final .pdfbar button:hover{background:#083b78}
body.final .pdfbar small{display:block;font-weight:400;font-size:.72rem;
 opacity:.85}
@media (max-width:52rem){body.final .sheet{width:100%;max-width:100%;margin:0;
 padding:1.4rem 1.1rem;box-shadow:none}body.final .pdfbar{top:auto;bottom:14px}}
@page{size:A4;margin:22mm 20mm}
@media print{
 html.final,body.final{background:#fff}
 body.final .sheet{width:auto;max-width:none;margin:0;padding:0;
  box-shadow:none;overflow:hidden}
 body.final .pdfbar{display:none}
 body{max-width:none;margin:0;font-size:11pt;padding:0;overflow:hidden}
 /* تور امن: هیچ عنصری نمی‌تواند پهن‌تر از جعبه‌ی صفحه شود */
 .sheet *{max-width:100%;min-width:0}
 p,li,td,th,figcaption,h1,h2,h3{overflow-wrap:break-word}
 a.pn,.hint,.toc{display:none}
 .cover{min-height:auto;height:235mm;page-break-after:always;break-after:page;
  margin:0}
 figure,.tblwrap{break-inside:avoid}
 h2,h3{page-break-after:avoid;break-after:avoid}
 figure,.eq{page-break-inside:avoid}
 figure img{border:0;padding:0;max-width:100%}
 a{color:inherit;text-decoration:none}
 /* جدول: چیدمان ثابت = عرض جدول هرگز از صفحه بیشتر نمی‌شود */
 .tblwrap{overflow:visible}
 table{width:100%;table-layout:fixed;font-size:8.5pt;line-height:1.6}
 th,td{padding:.25rem .5rem;white-space:normal;word-wrap:break-word;
  overflow-wrap:anywhere}
 /* رابطه‌ها: کوچک‌سازی + مقیاس SVG؛ اگر باز هم بلند بود بریده می‌شود
    نه اینکه از صفحه بیرون بزند */
 .eq{font-size:9pt;overflow:hidden}
 mjx-container{max-width:100% !important}
 mjx-container svg{max-width:100% !important;height:auto !important}
 ol.refs li{font-size:8.5pt}
}
</style>
<script>
window.MathJax={tex:{inlineMath:[['\\\\(','\\\\)']],tags:'none',
 macros:{Fp:'F_p',nm:['#1\\\\,\\\\text{nm}',1]}},options:{enableMenu:false}};
</script>
<script defer src="@@MJ@@"></script>
</head><body class="@@CLS@@">
@@PDFBAR@@<div class="@@SHEET@@">
<div class="cover">
  <div class="cover-top">دانشگاه اصفهان
    <small>دانشکده‌ی علوم — گروه فیزیک</small></div>
  <div class="cover-title">@@T@@</div>
  <div>
    <div class="cover-authors">امین حسین سدیدی &nbsp;·&nbsp;
      سید محمد پارسا مولایی طبری
      <small>دانشجویان کارشناسی فیزیک</small></div>
    <div class="cover-advisor">استاد راهنما: <b>دکتر مالک باقری هارونی</b></div>
  </div>
  <div class="cover-bottom">پروژه‌ی کارشناسی فیزیک — نیم‌سال ۱۴۰۴–۱۴۰۵<br>
    شهریور ۱۴۰۵</div>
</div>
<h1 class="maintitle">@@T@@</h1>
<div class="byline">
<p class="authors">امین حسین سدیدی &nbsp;·&nbsp; سید محمد پارسا مولایی طبری</p>
<p class="affil">دانشجویان کارشناسی فیزیک، گروه فیزیک، دانشگاه اصفهان</p>
<p class="advisor">استاد راهنما: دکتر مالک باقری هارونی</p>
<p class="affil">عضو هیئت علمی گروه فیزیک، دانشگاه اصفهان</p>
</div>
<div class="hint">
<b>این یک پیش‌نمایش برای بازبینی است، نه نسخه‌ی نهایی.</b>
صفحه‌آرایی، شماره‌ی صفحه و شکستِ سطرها در PDF نهایی (XeLaTeX) تعیین
می‌شود؛ اینجا فقط متن، فرمول‌ها، شکل‌ها و مراجع را ببینید.
عددِ خاکستریِ کنار هر پاراگراف شماره‌ی همان پاراگراف است — در بازخوردتان
به همان شماره ارجاع دهید (مثلاً «پاراگراف ۱۴، جمله‌ی دوم»). با کلیک روی
شماره، نشانی همان پاراگراف در نوار آدرس می‌آید و می‌توانید لینکش را
بفرستید. کلیک روی نمودارها نسخه‌ی برداری‌شان را باز می‌کند.
</div>
<div class="abs"><h2>چکیده</h2>@@ABS@@</div>
<p class="kw"><b>کلیدواژه‌ها:</b> @@KW@@</p>
<nav class="toc"><b>فهرست</b>@@TOC@@</nav>
@@BODY@@
<h2 id="refs">مراجع</h2>
<ol class="refs">@@REFS@@</ol>
@@FOOT@@
</div>
</body></html>
"""


FINAL = '--final' in sys.argv
PDFBAR = ('<div class="pdfbar"><button type="button" onclick="window.print()">'
          '\u062f\u0627\u0646\u0644\u0648\u062f PDF'
          '<small>\u062f\u0631 \u067e\u0646\u062c\u0631\u0647\u200c\u06cc \u0628\u0627\u0632\u0634\u062f\u0647 \u00ab\u0630\u062e\u06cc\u0631\u0647 \u0628\u0647 \u0635\u0648\u0631\u062a PDF\u00bb \u0631\u0627 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646\u06cc\u062f</small>'
          '</button></div>')

def main():
    main_tex = read_tex(os.path.join(MS, 'main.tex'))

    tm = re.search(r'\\title\{', main_tex)
    title = ' '.join(group(main_tex, tm.end() - 1)[0].split()) if tm else ''

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
    # کلیدواژه‌ها به‌صورت خط ساده‌ی رسمی (تم دانشگاهی)
    kw_html = inline(' '.join(take_math(keywords).split()))
    text = take_floats(take_math('\n\n'.join(src)))
    main_html = body_html(text, number=True)

    toc = '\n'.join('<div class="%s"><a href="#%s">%s%s</a></div>'
                    % ('s' if tag == 'h3' else 'm', html.escape(a),
                       ('<span class="n">%s</span> ' % num) if num else '', t)
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
    for k, v in (('@@T@@', inline(title)), ('@@ABS@@', abs_html),
                 ('@@KW@@', kw_html), ('@@TOC@@', toc),
                 ('@@BODY@@', main_html), ('@@REFS@@', '\n'.join(refs)),
                 ('@@MJ@@', mj), ('@@CLS@@', 'final' if FINAL else ''), ('@@SHEET@@', 'sheet' if FINAL else ''), ('@@PDFBAR@@', PDFBAR if FINAL else ''), ('@@FOOT@@', '<p class="foot">دانشگاه اصفهان — گروه فیزیک — ۱۴۰۵</p>' if FINAL else '')):
        doc = doc.replace(k, v)
    if FINAL:
        doc = re.sub(r'<div class="hint">.*?</div>\s*', '', doc, count=1, flags=re.S)
        doc = re.sub(r'<nav class="toc">.*?</nav>\s*', '', doc, count=1, flags=re.S)
        doc = re.sub(r'<a class="pn"[^>]*>[^<]*</a>', '', doc)
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

    doc, imgs = inline_images(doc)
    print('تصویرهای جاسازی‌شده: %s' % (', '.join(imgs) if imgs else 'هیچ'))
    doc, mj_in = inline_mathjax(doc)
    print('MathJax: %s' % ('درون‌خطی (خودبسنده)' if mj_in
                           else 'برچسب src (نیازمند فایل کنار صفحه)'))
    if FINAL:
        # در نسخه‌ی نهایی، پیوند «نسخه‌ی برداری» دور تصویر حذف می‌شود:
        # فایل تک‌فایل است و PDF کنار آن وجود ندارد.
        doc = re.sub(r'<a href="figures/[^"]+\.pdf"[^>]*>(<img[^>]+>)</a>',
                     r'\1', doc)

    open(OUT, 'w', encoding='utf-8', newline='\n').write(doc)

    print('نوشته شد: %s  (%d کیلوبایت)'
          % (OUT, len(doc.encode('utf-8')) // 1024))
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

"""نسخه‌ی نهایی تک‌فایلی مقاله: python3 tools/make_final_html.py
→ مقاله_نسخه_نهایی.html (شکل‌ها، قلم و MathJax همه داخل فایل؛ آفلاین)"""
import re, base64, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MS = os.path.join(ROOT, 'manuscript')
subprocess.check_call([sys.executable, os.path.join(ROOT, 'tools', 'tex2html.py'), '--final'])
s = open(os.path.join(MS, 'final.html'), encoding='utf-8').read()
def img(m):
    p = os.path.join(MS, m.group(1))
    return 'src="data:image/png;base64,%s"' % base64.b64encode(open(p, 'rb').read()).decode()
s = re.sub(r'src="(figures/web/[^"]+\.png)"', img, s)
s = re.sub(r'<a href="figures/[^"]+\.pdf"[^>]*>(<img[^>]+>)</a>', r'\1', s)
m = re.search(r'<script defer src="([^"]+)"></script>', s)
js = open(os.path.join(MS, m.group(1)), encoding='utf-8').read()
s = s.replace(m.group(0), '<script>' + js.replace('</script>', '<\\/script>') + '</script>')
out = os.path.join(ROOT, 'مقاله_نسخه_نهایی.html')
open(out, 'w', encoding='utf-8').write(s)
pv = os.path.join(ROOT, 'maghale-preview')
if os.path.isdir(pv):
    open(os.path.join(pv, 'final.html'), 'w', encoding='utf-8').write(s)
print('نوشته شد:', out, len(s) // 1024, 'KB')

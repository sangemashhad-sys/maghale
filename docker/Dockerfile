# ===================================================================
#  تصویر داکر برای کامپایل مقاله‌ی فارسی با XeLaTeX
#  ---------------------------------------------------------------
#  چرا Alpine و نه یکی از تصویرهای آماده‌ی TeX Live؟
#  در این محیط، رجیستری داکر فقط تصویرهای کَش‌شده‌ی محلی را می‌دهد و
#  `docker pull texlive/texlive` و `ghcr.io/...` هر دو با
#  «RBAC: access denied» یا «TLS handshake timeout» شکست می‌خورند.
#  اما `alpine:3.20` از قبل موجود است و مخزن بسته‌های apk در دسترس
#  است؛ پس TeX Live را از apk نصب می‌کنیم.
#
#  چرا نصب در چند لایه‌ی جدا و با تلاش مکرر؟
#  دانلود از dl-cdn.alpinelinux.org در این شبکه ناپایدار است و اجرای
#  یک‌جای همه‌ی بسته‌ها با «BAD archive / I/O error» می‌شکست. با تفکیک
#  لایه‌ها، هر تلاش دوباره از کَش لایه‌های موفق ادامه می‌دهد.
#
#  بسته‌ی texmf-dist-latexextra عمداً نصب نمی‌شود: حجم آن (همراه
#  texmf-dist-pictures) بیش از یک گیگابایت است و مقاله به هیچ سبک آن
#  نیاز ندارد. لایه‌ی پایانی همین را بررسی می‌کند: اگر روزی سبکی از آن
#  مجموعه لازم شد، ساخت تصویر با پیام روشن شکست می‌خورد.
#
#  ساخت:
#    docker build -t maghale-tex docker
#  اجرا:
#    powershell -File docker\build.ps1
# ===================================================================
FROM alpine:3.20

# تابع کمکی: تلاش مکرر برای apk add (شبکه‌ی ناپایدار)
RUN printf '%s\n' \
      '#!/bin/sh' \
      'set -eu' \
      'i=1' \
      'while [ "$i" -le 5 ]; do' \
      '  apk add --no-cache "$@" && exit 0' \
      '  echo "apk add failed (attempt $i) — retrying in 10s: $*" >&2' \
      '  i=$((i+1)); sleep 10' \
      'done' \
      'echo "apk add gave up after 5 attempts: $*" >&2; exit 1' \
    > /usr/local/bin/apk-try && chmod +x /usr/local/bin/apk-try

# --- ۱) موتور xelatex + fontconfig --------------------------------
RUN apk-try texlive-xetex fontconfig

# --- ۲) هسته‌ی LaTeX و بسته‌های توصیه‌شده --------------------------
#  geometry, caption, booktabs, hyperref, xcolor, graphicx از این دو می‌آید
RUN apk-try texmf-dist-latex texmf-dist-latexrecommended

# --- ۳) فارسی‌نویسی: xepersian و bidi -----------------------------
RUN apk-try texmf-dist-langarabic

# --- ۴) ریاضیات و قلم‌های استاندارد (TeX Gyre Termes) --------------
RUN apk-try texmf-dist-mathscience texmf-dist-fontsrecommended

# --- ۵) کتاب‌نامه: biblatex + biber -------------------------------
RUN apk-try texmf-dist-bibtexextra biber

# --- ۶) قلم جانشین فارسی (قلم اصلی، وزیرمتن، در manuscript/fonts است)
RUN apk-try font-noto-arabic && fc-cache -f

# --- ۷) راستی‌آزمایی: همه‌ی سبک‌های مورد نیاز main.tex موجودند؟ -----
RUN missing=''; \
    for s in xepersian.sty bidi.sty amsmath.sty amssymb.sty graphicx.sty \
             booktabs.sty caption.sty geometry.sty xcolor.sty \
             hyperref.sty biblatex.sty fontspec.sty; do \
      kpsewhich "$s" >/dev/null 2>&1 || missing="$missing $s"; \
    done; \
    if [ -n "$missing" ]; then \
      echo "سبک‌های یافت‌نشده:$missing" >&2; \
      echo "بسته‌ی apk مربوطه را به Dockerfile بیفزایید." >&2; \
      exit 1; \
    fi; \
    echo "همه‌ی سبک‌های لازم موجود است."; \
    xelatex --version | head -1; biber --version

COPY latex-run.sh /usr/local/bin/latex-run.sh
RUN chmod +x /usr/local/bin/latex-run.sh

WORKDIR /doc
ENTRYPOINT ["sh", "/usr/local/bin/latex-run.sh"]

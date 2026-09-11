#!/bin/sh
# ===================================================================
#  چرخه‌ی کامل کامپایل: xelatex → biber → xelatex → xelatex
#  در تصویر maghale-tex اجرا می‌شود؛ /doc همان manuscript/ است.
#
#  خروجی هر مرحله در build.log جمع می‌شود تا در ویندوز خواندنی باشد
#  (چاپ مستقیم متن فارسی روی کنسول cp1256 خطای رمزگذاری می‌دهد).
# ===================================================================
set -eu

JOB=${1:-main}
LOG=/doc/build.log

: > "$LOG"

log() { printf '\n===== %s =====\n' "$1" >> "$LOG"; }

# مرحله‌ی ۱ — اجرای اول: ساختن .aux و .bcf
log "xelatex pass 1"
xelatex -interaction=nonstopmode -halt-on-error -file-line-error \
        "$JOB" >> "$LOG" 2>&1 || {
  echo "FAILED: xelatex pass 1 — see manuscript/build.log"
  grep -E '^[^ ]+\.(tex|sty):[0-9]+:' "$LOG" | head -20
  exit 1
}

# مرحله‌ی ۲ — کتاب‌نامه
log "biber"
biber "$JOB" >> "$LOG" 2>&1 || {
  echo "FAILED: biber — see manuscript/build.log"
  tail -30 "$LOG"
  exit 1
}

# مرحله‌های ۳ و ۴ — حل ارجاع‌های متقابل و شماره‌گذاری مراجع
for pass in 2 3; do
  log "xelatex pass $pass"
  xelatex -interaction=nonstopmode -halt-on-error -file-line-error \
          "$JOB" >> "$LOG" 2>&1 || {
    echo "FAILED: xelatex pass $pass — see manuscript/build.log"
    grep -E '^[^ ]+\.(tex|sty):[0-9]+:' "$LOG" | head -20
    exit 1
  }
done

# --- خلاصه‌ی وضعیت ---------------------------------------------------
log "summary"
{
  echo "--- undefined references / citations ---"
  grep -i 'undefined' "$LOG" || echo "(none)"
  echo "--- overfull boxes (>10pt) ---"
  grep -E 'Overfull .*(1[0-9]{1,}|[2-9][0-9])\.[0-9]+pt' "$LOG" | head -20 \
    || echo "(none)"
} >> "$LOG" 2>&1

if [ -f "/doc/$JOB.pdf" ]; then
  PAGES=$(grep -o 'Output written on .* ([0-9]* page' "$LOG" | tail -1 \
          | grep -o '[0-9]*' | tail -1)
  echo "OK: $JOB.pdf built, pages=${PAGES:-?}"
else
  echo "FAILED: no PDF produced — see manuscript/build.log"
  exit 1
fi

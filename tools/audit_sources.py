# -*- coding: utf-8 -*-
"""
بازبینی (audit) همه‌ی منابع و امتیازدهی به میزان کاربردی بودنشان
برای مقاله‌ی: «نقد مدل‌های همسانگرد (ضرایب اینشتین/مدل لایه‌ای) در گسیل
خودبه‌خودی گسیل‌گر کوانتومی مجاور نانومیله پلاسمونی طلا — 3D-FDTD»

خروجی: D:\\مقاله\\evidence\\source_audit.md
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf

ROOT = Path(r"D:\مقاله")
SRC_DIRS = [ROOT / "google scholar articel", ROOT / "مقالات رایگان گوگل اسکولار"]
OUT = ROOT / "evidence" / "source_audit.md"

EXCLUDE = {"chat about articel.txt", "first artcel text.txt"}

# (نام محور، وزن، الگو) — وزن بالاتر = مرتبط‌تر با هسته‌ی مقاله
AXES: list[tuple[str, int, str]] = [
    ("نانومیله/نانوراد طلا", 5, r"gold nanorod|Au nanorod|gold nano-?rod|nanorod|nanospheroid"),
    ("فاکتور پورسل", 5, r"Purcell factor|Purcell enhancement|Purcell effect"),
    ("گسیل‌گر دوقطبی نقطه‌ای", 4, r"dipole (source|emitter)|point dipole|quantum emitter|single (molecule|photon) emitter"),
    ("FDTD / Lumerical", 3, r"\bFDTD\b|finite-?difference time-?domain|Lumerical"),
    ("کوئنچینگ و بازده تابشی", 4, r"quench\w+|radiative efficiency|antenna efficiency|apparent quantum (yield|efficiency)|nonradiative decay"),
    ("ضرایب اینشتین / دو-ترازی", 6, r"Einstein (A|B )?coefficient|Einstein's? coefficient|two-?level (atom|system)|spontaneous emission rate"),
    ("ناهمسانگردی و جهت‌گیری دوقطبی", 5, r"anisotrop\w+|dipole orientation|orientation[- ]dependen\w+|longitudinal (LSPR|plasmon|mode)|transverse mode|polari[sz]ation[- ]dependen\w+"),
    ("LDOS / تابع گرین", 4, r"local density of (optical |photonic )?states|\bLDOS\b|dyadic Green|Green'?s? function|Fermi'?s? golden rule"),
    ("مقایسه با کره / نظریه‌ی می", 4, r"Mie theor\w*|spherical (nanoparticle|particle)s?|equal-?volume sphere|non-?spherical|spherical harmonic"),
    ("داده‌ی نوری طلا", 2, r"Johnson (and|&) Christy|dielectric function of gold|permittivity of gold|Drude(-Lorentz)? model"),
    ("تقویت فلورسانس (MEF/SERS)", 2, r"metal-?enhanced fluorescence|\bMEF\b|\bSERS\b|fluorescence enhancement"),
    ("تشدید LSPR", 2, r"localized surface plasmon resonance|\bLSPR\b|plasmon resonance"),
]

# آستانه‌های طبقه‌بندی
T_CORE, T_SUPPORT, T_MARGINAL = 60, 30, 12


def extract(path: Path) -> str:
    if path.suffix.lower() == ".txt":
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:                                     # noqa: BLE001
            return ""
    try:
        with pymupdf.open(path) as doc:
            pages = min(len(doc), 40)          # ۴۰ صفحه‌ی اول برای سرعت
            return "\n".join(doc[i].get_text() for i in range(pages))
    except Exception:                                         # noqa: BLE001
        return ""


def main() -> int:
    rows = []
    for directory in SRC_DIRS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.name in EXCLUDE:
                continue
            if path.suffix.lower() not in {".pdf", ".txt"}:
                continue
            text = extract(path)
            if not text.strip():
                rows.append((path.name, 0, ["متن استخراج نشد (اسکن‌شده؟)"], "بازبینی دستی"))
                continue
            score = 0
            matched = []
            for name, weight, pat in AXES:
                n = len(re.findall(pat, text, re.IGNORECASE))
                if n:
                    score += weight * min(n, 8)   # سقف برای جلوگیری از تورم
                    matched.append(f"{name}({n})")
            if score >= T_CORE:
                cls = "هسته‌ای"
            elif score >= T_SUPPORT:
                cls = "پشتیبان"
            elif score >= T_MARGINAL:
                cls = "حاشیه‌ای"
            else:
                cls = "بی‌ربط"
            rows.append((path.name, score, matched, cls))

    rows.sort(key=lambda r: -r[1])
    order = {"هسته‌ای": 0, "پشتیبان": 1, "حاشیه‌ای": 2, "بی‌ربط": 3, "بازبینی دستی": 4}
    counts: dict[str, int] = {}
    for _n, _s, _m, cls in rows:
        counts[cls] = counts.get(cls, 0) + 1

    lines = [
        "# بازبینی کاربردی‌بودن منابع",
        "",
        "امتیاز بر پایه‌ی حضور محورهای هسته‌ی مقاله (نانومیله طلا، پورسل، ضرایب اینشتین،",
        "ناهمسانگردی، LDOS، کوئنچینگ، FDTD) محاسبه شده است.",
        "",
        "## خلاصه",
        "",
        "| طبقه | تعداد |",
        "| --- | --- |",
    ]
    for cls in sorted(counts, key=lambda c: order.get(c, 9)):
        lines.append(f"| {cls} | {counts[cls]} |")
    lines += ["", f"جمع: **{len(rows)}** سند", "", "## جدول کامل", "",
              "| منبع | امتیاز | طبقه | محورهای یافت‌شده |", "| --- | --- | --- | --- |"]
    for name, score, matched, cls in rows:
        lines.append(f"| {name} | {score} | {cls} | {', '.join(matched[:6]) or '—'} |")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"نوشته شد: {OUT}")
    for cls in sorted(counts, key=lambda c: order.get(c, 9)):
        print(f"  {cls}: {counts[cls]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

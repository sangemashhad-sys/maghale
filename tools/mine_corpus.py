# -*- coding: utf-8 -*-
"""
استخراج شواهد علمی از مجموعه منابع (PDF و TXT) برای مقاله‌ی نقدی:
«ناکارآمدی طبقه‌بندی لایه‌ای s, p, d (مبتنی بر تقارن کروی) در هندسه استوانه‌ای»

خروجی: D:\\مقاله\\evidence\\<topic>.md به همراه evidence\\index.md
هر شاهد شامل: نام فایل منبع، شماره صفحه (PDF) یا خط (TXT)، و متن پاراگراف.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(r"D:\مقاله")
SRC_DIRS = [ROOT, ROOT / "google scholar articel", ROOT / "مقالات رایگان گوگل اسکولار"]
OUT_DIR = ROOT / "evidence"

# فایل‌های گفتگوی شخصی / پیش‌نویس خودمان که منبع علمی نیستند
EXCLUDE_NAMES = {
    "مدل لایه_ای اتم و ضرایب اینشتین، اگ.txt",
    "متن اولیه مقاله.txt",
    "chat about articel.txt",
    "first artcel text.txt",
}

WORD_MIN = 25          # حداقل تعداد کلمه‌ی یک پاراگراف معتبر
MAX_HITS_PER_TOPIC = 60
SNIPPET_MAX = 1400     # حداکثر طول متن هر شاهد

# هر موضوع: (کلید خروجی، عنوان فارسی، الگوی regex)
TOPICS: list[tuple[str, str, str]] = [
    (
        "01_cylindrical_symmetry",
        "تقارن استوانه‌ای / محوری و مختصات استوانه‌ای",
        r"cylindric\w*|axial symmetr\w*|axisymmetr\w*|rotational symmetry about|"
        r"C∞v|continuous rotational symmetry",
    ),
    (
        "02_spherical_basis_spd",
        "پایه‌ی کروی، هارمونیک‌های کروی و برچسب‌های s/p/d",
        r"spherical harmonic\w*|multipole expansion|Mie theor\w*|"
        r"dipolar and quadrupolar|dipole, quadrupole|"
        r"\b[spd][- ]?(like )?(orbital|shell)s?\b",
    ),
    (
        "03_quantum_numbers",
        "اعداد کوانتومی l و m، تبهگنی و شکست آن",
        r"azimuthal quantum number|orbital quantum number|"
        r"angular momentum quantum number|degenerac\w+|lift\w* the degenerac\w+",
    ),
    (
        "04_symmetry_breaking",
        "شکست تقارن کروی و پیامدهای طیفی آن",
        r"symmetry break\w*|breaking of (the )?symmetry|reduced symmetry|"
        r"lower(ed)? symmetry|deviation from spher\w*|non-?spherical",
    ),
    (
        "05_selection_rules",
        "قواعد گزینش، مدهای تاریک و مدهای غیرتابشی",
        r"selection rule\w*|dark mode\w*|bright mode\w*|"
        r"optically (in)?active mode\w*|non-?radiativ\w+ mode\w*|dipole-?forbidden",
    ),
    (
        "06_hybridization_model",
        "مدل هیبریداسیون پلاسمونی (قیاس با اوربیتال مولکولی)",
        r"plasmon hybridi[sz]ation|hybridi[sz]ation model|molecular orbital theor\w*|"
        r"bonding and antibonding|antibonding",
    ),
    (
        "07_anisotropy_polarization",
        "ناهمسانگردی و وابستگی به قطبش/جهت‌گیری دوقطبی",
        r"anisotrop\w+|isotropic assumption|polari[sz]ation[- ]dependen\w+|"
        r"orientation[- ]dependen\w+|dipole orientation|longitudinal and transverse mode",
    ),
    (
        "08_ldos_purcell",
        "LDOS، فاکتور پورسل و تابع گرین (چارچوب نظری)",
        r"local density of (optical |photonic )?states|\bLDOS\b|Purcell factor|"
        r"Green'?s? (dyadic |tensor )?function|dyadic Green",
    ),
    (
        "09_model_limitations",
        "محدودیت و ناکارآمدی مدل‌های تحلیلی/کروی (سوخت اصلی نقد)",
        r"limitation\w* of|breaks? down|fails? to (describe|predict|capture|account)|"
        r"is not (valid|applicable|sufficient)|no longer valid|"
        r"cannot be (applied|used|described)|inadequa\w+|oversimplifi\w+|"
        r"poor convergence|does not converge",
    ),
    (
        "10_numerical_necessity",
        "ضرورت روش‌های عددی (FDTD/BEM/DDA) به جای حل تحلیلی",
        r"\bFDTD\b|finite-?difference time-?domain|boundary element method|"
        r"discrete dipole approximation|\bDDA\b|no analytical solution|"
        r"analytical(ly)? (solution|tractable|intractable)",
    ),
    (
        "11_nanowire_waveguide_modes",
        "مدهای نانوسیم/موج‌بر استوانه‌ای (پایه‌ی درست در هندسه استوانه‌ای)",
        r"nanowire|nano-?wire|cylindrical waveguide|guided mode\w*|leaky mode\w*|"
        r"Bessel function\w*|propagation constant|azimuthal (index|order|number)",
    ),
    (
        "12_quantum_confinement",
        "محدودشدگی کوانتومی در هندسه استوانه‌ای (چاه/سیم/نقطه کوانتومی)",
        r"quantum confinement|quantum wire|envelope function|"
        r"effective mass approximation|confined electron state\w*",
    ),
]


def clean(text: str) -> str:
    """نرمال‌سازی متن: اتصال کلمات شکسته‌شده و یکدست‌کردن فاصله‌ها."""
    text = re.sub(r"-\r?\n(?=[a-z])", "", text)
    text = re.sub(r"[ \t]*\r?\n[ \t]*", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def iter_pdf_paragraphs(path: Path):
    """تولید (شماره صفحه، پاراگراف) برای هر بلوک متنی PDF."""
    try:
        doc = pymupdf.open(path)
    except Exception as exc:                              # noqa: BLE001
        print(f"  [skip] {path.name}: {exc}", file=sys.stderr)
        return
    with doc:
        for pno, page in enumerate(doc, start=1):
            try:
                blocks = page.get_text("blocks")
            except Exception:                             # noqa: BLE001
                continue
            for block in blocks:
                para = clean(block[4] or "")
                if len(para.split()) >= WORD_MIN:
                    yield pno, para


def iter_txt_paragraphs(path: Path):
    """تولید (شماره خط، پاراگراف) برای فایل‌های متنی."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:                              # noqa: BLE001
        print(f"  [skip] {path.name}: {exc}", file=sys.stderr)
        return
    for lineno, line in enumerate(content.splitlines(), start=1):
        for para in re.split(r"(?<=[.!?])\s{2,}", line):
            para = clean(para)
            if len(para.split()) >= WORD_MIN:
                yield lineno, para


def collect_sources() -> list[Path]:
    files: list[Path] = []
    for directory in SRC_DIRS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.name in EXCLUDE_NAMES:
                continue
            if path.suffix.lower() in {".pdf", ".txt"}:
                files.append(path)
    return files


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    patterns = {key: re.compile(pat, re.IGNORECASE) for key, _title, pat in TOPICS}
    hits: dict[str, list[tuple[str, str, str]]] = {key: [] for key, _t, _p in TOPICS}
    seen: dict[str, set[str]] = {key: set() for key, _t, _p in TOPICS}

    sources = collect_sources()
    print(f"تعداد اسناد برای پردازش: {len(sources)}")

    for path in sources:
        print(f"- {path.name}")
        is_pdf = path.suffix.lower() == ".pdf"
        walker = iter_pdf_paragraphs if is_pdf else iter_txt_paragraphs
        for loc, para in walker(path):
            for key, rx in patterns.items():
                if len(hits[key]) >= MAX_HITS_PER_TOPIC or not rx.search(para):
                    continue
                fingerprint = para[:180].lower()
                if fingerprint in seen[key]:
                    continue
                seen[key].add(fingerprint)
                label = f"p.{loc}" if is_pdf else f"line {loc}"
                hits[key].append((path.name, label, para[:SNIPPET_MAX]))

    index_lines = [
        "# فهرست شواهد استخراج‌شده از منابع",
        "",
        f"تعداد اسناد پردازش‌شده: **{len(sources)}**",
        "",
        "| # | موضوع | تعداد شاهد | فایل |",
        "| - | ----- | ---------- | ---- |",
    ]
    for idx, (key, title, _pat) in enumerate(TOPICS, start=1):
        rows = hits[key]
        body = [f"# {title}", "", f"تعداد شاهد: {len(rows)}", ""]
        for n, (fname, label, para) in enumerate(rows, start=1):
            body += [f"## شاهد {n} — {fname} ({label})", "", f"> {para}", ""]
        (OUT_DIR / f"{key}.md").write_text("\n".join(body), encoding="utf-8")
        index_lines.append(f"| {idx} | {title} | {len(rows)} | `{key}.md` |")

    (OUT_DIR / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print("\nخروجی در:", OUT_DIR)
    for key, _t, _p in TOPICS:
        print(f"  {key}: {len(hits[key])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

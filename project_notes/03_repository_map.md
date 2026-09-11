# نقشه مخزن و نقش فایل‌ها

## فایل‌های مرجع اصلی

| مسیر | نقش | وضعیت |
|---|---|---|
| `first artcel text.txt` | متن مقاله عددی پیش از توسعه نظری | مرجع اصلی برای شناخت هسته پژوهش |
| `chat about articel.txt` | تاریخچه آموزش، طراحی، اجرای دستی و نگارش | بسیار مهم؛ ۸۸۴۵ خط |
| `manuscript/main.tex` | نسخه جاری مقاله | نسخه هدف برای ادامه |
| `manuscript/sections/*.tex` | پنج بخش نسخه جاری | ترکیب متن پایه و افزوده‌ها |
| `manuscript/references.bib` | کتاب‌نامه جاری | ۲۷ مدخل، همسان با `draft/references.bib` |

## لایه توسعه نظری

| مسیر | نقش |
|---|---|
| `evidence/roadmap.md` | تعریف پروژه نقدی و سپس تصمیم ادغام |
| `evidence/outline.md` | معماری نظری پیشنهادی |
| `evidence/integration_plan.md` | نگاشت دقیق افزوده‌ها به متن پایه |
| `evidence/synthesis.md` | جمع‌بندی شواهد استخراج‌شده |
| `evidence/source_audit.md` | ارزیابی منابع و ادعاهای عددی |
| `evidence/01...12_*.md` | قطعات استخراج‌شده از پیکره منابع؛ متن مقاله نیستند |
| `draft/*.md` | متن افزوده پیش از تبدیل به LaTeX |

## شبیه‌سازی و داده

| مسیر | نقش | نکته |
|---|---|---|
| `New folder (2)/B_freespace.fsp` | فایل باینری Lumerical | احتمالاً پروژه اجرای دستی؛ باید در Lumerical بازبینی شود |
| `simulation/nanorod_purcell.lsf` | اسکریپت بازسازی مدل و استخراج CSV | خروجی اجرای آن در مخزن نیست |
| `simulation/make_figures.py` | تولید شکل از CSV | برای داده‌های جدید |
| `manuscript/figures/Purcell_Spectrum.orig.pdf` | نمودار برداری اصلی خروجی Lumerical | زمان metadata: ۲۸ اوت ۲۰۲۶ |
| `manuscript/figures/radiated_power_T.orig.pdf` | نمودار برداری اصلی توان تابشی | خروجی Lumerical/VTK |
| `manuscript/figures/NearField_Profile.png` | تصویر میدان نزدیک | تصویر raster با ابعاد ۴۹۹×۴۰۶ |
| `_probe/*` | داده استخراج‌شده از مسیرهای برداری PDF | داده فیزیکی خام نیست؛ مختصات گرافیکی صفحه است |

## LaTeX و پیش‌نمایش

| مسیر | نقش |
|---|---|
| `manuscript/preview.html` | پیش‌نمایش خواندنی متن بدون موتور TeX |
| `index.html` | نسخه پیش‌نمایش در ریشه |
| `manuscript/fonts/` | فونت Vazirmatn محلی |
| `docker/` | تلاش قبلی برای محیط کامپایل؛ آزموده و تکمیل نشده |
| `manuscript/README.md` | راهنمای ساخت و وضعیت فعلی |

## کنترل‌های ماشینی موجود

- `evidence/check_manuscript.py`: ورودی‌ها، ارجاع‌ها، label/ref و ماکروها.
- `evidence/check_refs.py`: کلیدهای کتاب‌نامه پیش‌نویس.
- `tools/check_preview.py`: سلامت HTML.

این کنترل‌ها سلامت ساختاری را می‌سنجند، نه صحت فیزیکی ادعاها و نه بازتولید اعداد شبیه‌سازی.

## وضعیت شناخته‌شده کامپایل

در محیط فعلی فرمان‌های `xelatex`، `latexmk` و `biber` نصب نیستند. بررسی‌های استاتیک موفق‌اند، اما هنوز کامپایل واقعی نسخه جاری در این محیط انجام نشده است. بنابراین عبارت «LaTeX خراب است» ممکن است به محیط اجرا مربوط باشد، نه الزاماً syntax متن؛ این موضوع در مرحله مخصوص LaTeX تشخیص داده خواهد شد.

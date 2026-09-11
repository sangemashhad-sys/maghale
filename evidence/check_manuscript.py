r"""Validate the assembled LaTeX manuscript without running a TeX engine.

Usage: python evidence/check_manuscript.py
Output: evidence/_mscheck.txt

Checks performed:
  1. every \input{...} target exists
  2. every \cite key is defined in manuscript/references.bib
  3. manuscript/references.bib is identical to draft/references.bib
  4. brace balance per .tex file
  5. every \ref{...} has a matching \label{...} (and vice versa)
  6. no leftover [مرجع] placeholders
  7. inline math delimiters ($) come in pairs per file
"""
import glob
import os
import re

ROOT = 'manuscript'
BIB = os.path.join(ROOT, 'references.bib')
DRAFT_BIB = os.path.join('draft', 'references.bib')
OUT = 'evidence/_mscheck.txt'


def read(path: str) -> str:
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def strip_comments(text: str) -> str:
    """Drop LaTeX line comments so commented-out code is not validated."""
    return re.sub(r'(?<!\\)%.*', '', text)


def main() -> None:
    lines = []
    tex_files = [os.path.join(ROOT, 'main.tex')] + sorted(
        glob.glob(os.path.join(ROOT, 'sections', '*.tex')))
    lines.append('tex files: %d' % len(tex_files))

    bodies = {p: strip_comments(read(p)) for p in tex_files}

    # 1. \input targets
    missing_inputs = []
    for path, text in bodies.items():
        for m in re.finditer(r'\\input\{([^}]+)\}', text):
            target = os.path.join(ROOT, m.group(1))
            if not (os.path.isfile(target) or os.path.isfile(target + '.tex')):
                missing_inputs.append((path, m.group(1)))
    lines.append('missing \\input targets: %s' % (missing_inputs or 'none'))

    # 2. \cite keys
    bib = read(BIB)
    defined = set(re.findall(r'@\w+\{([^,\s]+)\s*,', bib))
    used = {}
    for path, text in bodies.items():
        for m in re.finditer(r'\\cite(?:\[[^\]]*\])?\{([^}]*)\}', text):
            for key in m.group(1).split(','):
                used.setdefault(key.strip(), set()).add(os.path.basename(path))
    undefined = sorted(k for k in used if k not in defined)
    lines.append('bib entries: %d ; cited keys: %d' % (len(defined), len(used)))
    lines.append('undefined cite keys: %s' % (undefined or 'none'))
    for k in undefined:
        lines.append('    %s <- %s' % (k, ', '.join(sorted(used[k]))))
    lines.append('bib entries never cited: %s'
                 % (sorted(defined - set(used)) or 'none'))

    # 3. bib copies in sync
    lines.append('references.bib matches draft/: %s'
                 % (read(BIB) == read(DRAFT_BIB)))

    # 4-7. per-file structural checks
    labels, refs = set(), {}
    for path, text in bodies.items():
        name = os.path.basename(path)
        if text.count('{') != text.count('}'):
            lines.append('BRACE MISMATCH in %s: %d open, %d close'
                         % (name, text.count('{'), text.count('}')))
        dollars = len(re.findall(r'(?<!\\)\$', text))
        if dollars % 2:
            lines.append('ODD $ COUNT in %s: %d' % (name, dollars))
        if 'مرجع]' in text:
            lines.append('PLACEHOLDER [مرجع] left in %s' % name)
        labels |= set(re.findall(r'\\label\{([^}]+)\}', text))
        for m in re.finditer(r'\\(?:eq)?ref\{([^}]+)\}', text):
            refs.setdefault(m.group(1), set()).add(name)

    lines.append('dangling \\ref targets: %s'
                 % (sorted(k for k in refs if k not in labels) or 'none'))
    # Section labels may legitimately stay unreferenced; figures, tables and
    # equations should be pointed at from the text.
    orphans = sorted(k for k in labels - set(refs) if not k.startswith('sec:'))
    lines.append('fig/tab/eq labels never referenced: %s' % (orphans or 'none'))
    lines.append('unreferenced section labels (informational): %s'
                 % sorted(k for k in labels - set(refs) if k.startswith('sec:')))

    # 8. math-only macros must appear inside math mode
    math_macros = ('Fp', 'nm')
    outside = []
    for path, text in bodies.items():
        # drop the \newcommand definitions themselves, then blank out every
        # math span, then look for leftover macro uses
        stripped = re.sub(r'\\newcommand\{\\\w+\}(?:\[\d+\])?\{[^\n]*\}',
                          '', text)
        stripped = re.sub(r'(?<!\\)\$[^$]*\$', '', stripped)
        stripped = re.sub(r'\\begin\{(equation|align)\*?\}.*?'
                          r'\\end\{\1\*?\}', '', stripped, flags=re.S)
        for macro in math_macros:
            for m in re.finditer(r'\\%s\b' % macro, stripped):
                line_no = stripped[:m.start()].count('\n') + 1
                outside.append('%s:~%d \\%s' % (os.path.basename(path),
                                                line_no, macro))
    lines.append('math macros used outside math mode: %s' % (outside or 'none'))

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('written', OUT)


if __name__ == '__main__':
    main()

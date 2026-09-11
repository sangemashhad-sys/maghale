r"""Validate that every \cite key used in draft/*.md exists in draft/references.bib.

Usage: python evidence/check_refs.py
Writes the report to evidence/_refcheck.txt (stdout is unreliable here).
"""
import glob
import re

BIB = 'draft/references.bib'
OUT = 'evidence/_refcheck.txt'


def main() -> None:
    bib = open(BIB, encoding='utf-8').read()
    defined = set(re.findall(r'@\w+\{([^,\s]+)\s*,', bib))

    used = {}
    for path in sorted(glob.glob('draft/*.md')):
        text = open(path, encoding='utf-8').read()
        for m in re.finditer(r'\\cite\{([^}]*)\}', text):
            for key in m.group(1).split(','):
                used.setdefault(key.strip(), set()).add(path)

    lines = ['DEFINED: %d' % len(defined), 'USED: %d' % len(used), '']

    missing = sorted(k for k in used if k not in defined)
    lines.append('MISSING (cited but not in .bib): %s' % (missing or 'none'))
    for k in missing:
        lines.append('    %s <- %s' % (k, ', '.join(sorted(used[k]))))

    unused = sorted(defined - set(used))
    lines.append('UNUSED in draft/*.md (expected: the 8 keys already cited by')
    lines.append('the existing article body, which is not a draft/*.md file):')
    for k in unused:
        lines.append('    %s' % k)

    lines.append('BRACES balanced: %s' % (bib.count('{') == bib.count('}')))
    lines.append('placeholders [مرجع]: %d' % bib.count('[مرجع]'))
    lines.append('duplicate keys: %s' % (
        sorted({k for k in re.findall(r'@\w+\{([^,\s]+)\s*,', bib)
                if re.findall(r'@\w+\{%s\s*,' % re.escape(k), bib).__len__() > 1})
        or 'none'))

    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('written', OUT)


if __name__ == '__main__':
    main()

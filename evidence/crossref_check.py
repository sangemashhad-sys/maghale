"""Fetch and condense Crossref records for the DOIs cited in section 4.5.

Usage: python evidence/crossref_check.py
Output: evidence/_crossref45.txt
"""
import json
import urllib.request

OUT = 'evidence/_crossref45.txt'
DOIS = [
    '10.1039/d5ra04583e',
    '10.1039/d5ra90101d',
    '10.1002/adpr.202100286',
]


def fetch(doi: str) -> dict:
    req = urllib.request.Request(
        'https://api.crossref.org/works/' + doi,
        headers={'User-Agent': 'ref-check/1.0 (mailto:none@example.com)'},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)['message']


def main() -> None:
    with open(OUT, 'w', encoding='utf-8') as out:
        for doi in DOIS:
            try:
                m = fetch(doi)
            except Exception as exc:
                out.write('%s -> FAILED: %s\n\n' % (doi, exc))
                continue
            authors = '; '.join(
                '%s, %s' % (a.get('family', '?'), a.get('given', ''))
                for a in m.get('author', [])
            )
            out.write('DOI      : %s\n' % m.get('DOI'))
            out.write('type     : %s\n' % m.get('type'))
            out.write('title    : %s\n' % ' | '.join(m.get('title', [])))
            out.write('journal  : %s\n' % ' | '.join(m.get('container-title', [])))
            out.write('volume   : %s\n' % m.get('volume'))
            out.write('issue    : %s\n' % m.get('issue'))
            out.write('page     : %s\n' % m.get('page'))
            out.write('art-num  : %s\n' % m.get('article-number'))
            out.write('year     : %s\n' % m.get('issued', {}).get('date-parts'))
            out.write('publisher: %s\n' % m.get('publisher'))
            out.write('authors  : %s\n' % authors)
            out.write('updates  : %s\n' % [
                (u.get('type'), u.get('DOI')) for u in m.get('update-to', [])
            ])
            out.write('updated-by: %s\n\n' % [
                (u.get('type'), u.get('DOI')) for u in m.get('updated-by', [])
            ])
    print('written', OUT)


if __name__ == '__main__':
    main()

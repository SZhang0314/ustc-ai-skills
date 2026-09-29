# -*- coding: utf-8 -*-
"""Detect the abstract block index for each paper JSON.

Returns (title_block_indices, abstract_index) where abstract_index is the index
of the para block holding the abstract text.
"""
import json
import glob
import re

TITLE_LIKE = re.compile(r'^\s*abstract\s*:?\s*$', re.I)
ABSTRACT_INLINE = re.compile(r'^\s*abstract\s*:?\s+', re.I)
DOI_RE = re.compile(r'^\s*(DOI|https?://|PACS|arXiv)', re.I)
DATED_RE = re.compile(r'^\s*\(?Dated', re.I)
KEYWD_RE = re.compile(r'^\s*[A-Za-z\- ]+ \| [A-Za-z]')


def norm(s):
    return re.sub(r'[\s\-–—:]+', '', (s or '').lower())


def is_author_or_affil(t, title_norm):
    if not t:
        return True
    # affiliation / author lines are short-ish, comma or digit heavy, no verb sentence
    if DOI_RE.match(t) or DATED_RE.match(t) or KEYWD_RE.match(t):
        return True
    # matches the paper title (or its first line)
    if title_norm and norm(t).startswith(title_norm[:25]):
        return True
    # no sentence ending and many commas / superscript digits -> author/affil
    words = t.split()
    if len(words) <= 25 and ',' in t and t.count(' ') < 40:
        return True
    return False


def detect(data):
    bs = data['blocks']
    title_norm = norm(data.get('title_en', ''))
    # case A: an explicit "Abstract" heading
    for i, b in enumerate(bs[:8]):
        if b.get('type') == 'heading' and TITLE_LIKE.match(b.get('en', '')):
            for j in range(i + 1, min(i + 4, len(bs))):
                if bs[j].get('type') == 'para' and len(bs[j].get('en', '')) > 60:
                    return j, 'heading'
    # case B: inline "Abstract:" prefix on a para
    for i, b in enumerate(bs[:4]):
        if b.get('type') == 'para' and ABSTRACT_INLINE.match(b.get('en', '')):
            return i, 'inline'
    # case C: first substantial para after skipping title/author/affil blocks
    for i, b in enumerate(bs[:8]):
        if b.get('type') != 'para':
            continue
        t = b.get('en', '')
        if len(t) < 120:
            continue
        if is_author_or_affil(t, title_norm):
            continue
        return i, 'first'
    return None, None


if __name__ == '__main__':
    for f in sorted(glob.glob('src/p??.json')):
        d = json.load(open(f, encoding='utf-8'))
        idx, how = detect(d)
        head = ''
        if idx is not None:
            head = d['blocks'][idx].get('en', '')[:60].encode('ascii', 'replace').decode()
        print(f"p{d['num']:02d} idx={idx} how={how} | {head}")

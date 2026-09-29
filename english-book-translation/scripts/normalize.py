# -*- coding: utf-8 -*-
"""Normalize unsupported Unicode characters to safe LaTeX equivalents.

Two modes:
- normalize(s): for plain TEXT fields. Maps glyphs missing from Times New Roman
  to LaTeX macros wrapped in $...$ (safe in text mode).
- normalize_math(s): for MATH content ($...$ inner spans, `equation` block
  `latex` fields). Maps Unicode math to pure LaTeX macros WITHOUT $ delimiters
  (nesting $ inside math would break).

Both run BEFORE LaTeX escaping (the renderers protect macro backslashes).
"""

# ---------- text-mode: char -> $macro$ or plain replacement ----------
MAP = {
    '\u27e8': '<',          # <
    '\u27e9': '>',          # >
    '\u2207': r'$\nabla$',  # nabla
    '\u20d7': '',           # combining arrow above (drop; keep base letter)
    '\u223c': r'$\sim$',    # tilde operator
    '\u22a5': r'$\perp$',   # perpendicular
    '\u2297': r'$\otimes$', # circled times
    '\u2217': '*',          # asterisk operator
    '\u2223': '|',          # divides
    '\u2218': r'$\circ$',   # ring operator
    '\u221d': r'$\propto$', # proportional to
    '\u2225': r'$\parallel$',  # parallel
    '\u2208': r'$\in$',     # element of
    '\u2243': r'$\simeq$',  # asymptotically equal
    '\u2213': r'$\mp$',     # minus-plus
    '\u226a': '<<',         # much less
    '\u226b': '>>',         # much greater
    '\u222c': 'int',        # double integral
    '\u22c5': r'$\cdot$',   # dot operator
    '\u2a7d': r'$\leqslant$',  # less-or-slant-equal
    '\u2a7e': r'$\geqslant$',  # greater-or-slant-equal
    '\u2272': r'$\lesssim$',   # less-similar
    '\u21d3': 'down',       # double down arrow
    '\u22ba': r'$\intercal$',  # transpose
    '\u2083': '3',          # subscript 3 (stragglers; agents should use $x_3$)
    '\u122c': 'H',          # Ethiopic (font artifact)
    '\u0d24': 't',          # Malayalam artifact
    '\u0dcd': '',           # Malayalam artifact (drop)
}

# Mathematical alphanumeric symbols -> ASCII/italic-safe letters.
import unicodedata


def _build_math_letters():
    out = {}
    explicit = {
        0x1D42B: 'r', 0x1D48C: 'm', 0x1D435: 'B', 0x1D451: 'd',
        0x1D439: 'F', 0x1D45A: 'n', 0x1D749: 'σ', 0x1D707: 'μ',
        0x1D6F9: 'ψ', 0x1D450: 'c', 0x1D43B: 'H', 0x1D45B: 'n',
        0x1D456: 'i', 0x1D471: 'j', 0x1D438: 'E', 0x1D43E: 'K',
        0x1D440: 'M', 0x1D70B: 'π', 0x1D444: 'Q', 0x1D447: 'T',
        0x1D48D: 'm', 0x1D454: 'g', 0x1D462: 'u', 0x1D446: 'S',
        0x1D750: 'τ', 0x1D44E: 'a', 0x1D467: 'z', 0x1D461: 't',
        0x1D43D: 'J', 0x1D496: 'v', 0x1D41F: 'f', 0x1D453: 'f',
        0x1D712: 'χ', 0x1D741: 'θ', 0x1D473: 'k', 0x1D46C: 'o',
        0x1D486: 'w', 0x1D468: 'A', 0x1D4AF: 't', 0x1D6FF: 'δ',
        0x1D70C: 'ρ', 0x1D459: 'l', 0x1D443: 'P', 0x1D436: 'C',
        0x1D474: 'l', 0x1D465: 'x', 0x1D466: 'y', 0x1D719: 'φ',
        0x1D497: 'v', 0x1D458: 'k', 0x1D401: 'B', 0x1D492: 'v',
        0x1D479: 'r', 0x1D706: 'λ', 0x1D405: 'F', 0x1D715: '∂',
        0x1D452: 'e', 0x1D70F: 'τ',
    }
    for cp, repl in explicit.items():
        out[chr(cp)] = repl
    return out


MATH_LETTERS = _build_math_letters()

# ---------- math-mode: Unicode -> pure LaTeX macro (no $ delimiters) ----------
MATH_MODE_MAP = {
    # Greek lowercase
    '\u03b1': r'\alpha', '\u03b2': r'\beta', '\u03b3': r'\gamma',
    '\u03b4': r'\delta', '\u03b5': r'\varepsilon', '\u03f5': r'\epsilon',
    '\u03b6': r'\zeta', '\u03b7': r'\eta', '\u03b8': r'\theta',
    '\u03b9': r'\iota', '\u03ba': r'\kappa', '\u03bb': r'\lambda',
    '\u03bc': r'\mu', '\u03bd': r'\nu', '\u03be': r'\xi',
    '\u03bf': 'o', '\u03c0': r'\pi', '\u03c1': r'\rho',
    '\u03c2': r'\varsigma', '\u03c3': r'\sigma', '\u03c4': r'\tau',
    '\u03c5': r'\upsilon', '\u03d5': r'\phi', '\u03c6': r'\varphi',
    '\u03c7': r'\chi', '\u03c8': r'\psi', '\u03c9': r'\omega',
    # Greek uppercase
    '\u0393': r'\Gamma', '\u0394': r'\Delta', '\u0398': r'\Theta',
    '\u039b': r'\Lambda', '\u039e': r'\Xi', '\u03a0': r'\Pi',
    '\u03a3': r'\Sigma', '\u03a5': r'\Upsilon', '\u03a6': r'\Phi',
    '\u03a8': r'\Psi', '\u03a9': r'\Omega',
    # Operators / symbols
    '\u210f': r'\hbar', '\u2113': r'\ell', '\u2202': r'\partial',
    '\u221e': r'\infty', '\u00d7': r'\times', '\u00f7': r'\div',
    '\u00b1': r'\pm', '\u2213': r'\mp', '\u22c5': r'\cdot',
    '\u2219': r'\bullet', '\u2264': r'\leq', '\u2265': r'\geq',
    '\u2260': r'\neq', '\u2248': r'\approx', '\u2243': r'\simeq',
    '\u2245': r'\cong', '\u2261': r'\equiv', '\u221d': r'\propto',
    '\u223c': r'\sim', '\u226a': r'\ll', '\u226b': r'\gg',
    '\u2272': r'\lesssim', '\u2273': r'\gtrsim',
    '\u2a7d': r'\leqslant', '\u2a7e': r'\geqslant',
    '\u2208': r'\in', '\u2209': r'\notin', '\u2282': r'\subset',
    '\u2286': r'\subseteq', '\u222a': r'\cup', '\u2229': r'\cap',
    '\u2205': r'\emptyset', '\u2200': r'\forall', '\u2203': r'\exists',
    '\u00ac': r'\neg', '\u2227': r'\wedge', '\u2228': r'\vee',
    '\u2295': r'\oplus', '\u2297': r'\otimes', '\u2299': r'\odot',
    '\u22a5': r'\perp', '\u2225': r'\parallel', '\u2220': r'\angle',
    '\u2192': r'\rightarrow', '\u2190': r'\leftarrow',
    '\u21d2': r'\Rightarrow', '\u21d4': r'\Leftrightarrow',
    '\u2194': r'\leftrightarrow', '\u21a6': r'\mapsto',
    '\u2191': r'\uparrow', '\u2193': r'\downarrow',
    '\u2211': r'\sum', '\u220f': r'\prod', '\u222b': r'\int',
    '\u222c': r'\iint', '\u221a': r'\sqrt',
    '\u27e8': r'\langle', '\u27e9': r'\rangle',
    '\u2032': "'", '\u2033': "''", '\u00b0': r'^{\circ}',
    '\u2217': '*', '\u2223': '|', '\u2212': '-', '\u2215': '/',
    '\u2026': r'\ldots', '\u22ef': r'\cdots',
    '\u00a0': ' ', '\u2009': ' ', '\u2003': ' ', '\u2005': ' ',
    '\u2007': ' ', '\u2008': ' ', '\u2002': ' ',
}


def normalize(s):
    """Text-mode normalization: unicode -> $macro$ / plain replacements."""
    if not s:
        return s
    for k, v in MATH_LETTERS.items():
        s = s.replace(k, v)
    for k, v in MAP.items():
        s = s.replace(k, v)
    s = s.replace('\u20d7', '')
    return s


def normalize_math(s):
    """Math-mode normalization: unicode -> pure LaTeX macro (NO $ delimiters).
    Also maps unicode sub/superscript digits to _{n} / ^{n}."""
    if not s:
        return s
    for k, v in MATH_MODE_MAP.items():
        s = s.replace(k, v)
    for i, ch in enumerate('₀₁₂₃₄₅₆₇₈₉'):
        s = s.replace(ch, '_{%d}' % i)
    for i, ch in enumerate('⁰¹²³⁴⁵⁶⁷⁸⁹'):
        s = s.replace(ch, '^{%d}' % i)
    return s

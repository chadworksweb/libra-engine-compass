"""Verbatim-text guard for the calibrator's quote-prone output fields.

Lifted VERBATIM from Rising Compass so the calibrator's contamination_note /
dogma_note scrub is byte-identical (parity). The Compass's short generated
fields must paraphrase, never reproduce, the text they read. The prompt asks
for paraphrase, but models occasionally quote anyway, so this is the
deterministic LOCK in the scoring path: any run of >= MIN_RUN consecutive words
appearing verbatim in BOTH the field and the source text is treated as a quote
and the field is cleared.

A 6-word window catches real reproduction while not flagging incidental short
phrases ("i love you", "in the dark") that are not protected expression.
Matching is whitespace/punctuation/case-insensitive.
"""

from __future__ import annotations

import re

# Consecutive shared words that count as a verbatim quote. Lower = stricter
# (more false positives); higher = looser (misses short hooks). 6 is the balance.
MIN_RUN = 6


def _normalize_words(text: str) -> list[str]:
    """Lowercase, drop punctuation, split on whitespace."""
    return re.sub(r"[^\w\s]", " ", (text or "").lower()).split()


def _lyric_ngrams(lyrics: str, n: int) -> set[str]:
    words = _normalize_words(lyrics)
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def has_verbatim_overlap(prose: str, lyrics: str, min_run: int = MIN_RUN) -> bool:
    """True if any run of >= min_run consecutive words appears in both texts."""
    if not prose or not lyrics:
        return False
    grams = _lyric_ngrams(lyrics, min_run)
    if not grams:
        return False
    pwords = _normalize_words(prose)
    return any(
        " ".join(pwords[i:i + min_run]) in grams
        for i in range(len(pwords) - min_run + 1)
    )

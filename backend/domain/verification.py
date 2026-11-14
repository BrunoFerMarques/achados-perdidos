"""Ownership verification (scope §7): how well a claimant's answers match the expected ones."""

import unicodedata
from collections.abc import Sequence

# a typo is tolerated only in longer answers: a 4-digit serial number must be exact
TYPO_TOLERANCE_MIN_LENGTH = 5
# scope §12: below it the claim is rejected at once, otherwise an attendant reviews it
MIN_SCORE = 0.6


def normalize(answer: str) -> str:
    """Lowercase, no accents, punctuation as a separator and single spaces."""
    decomposed = unicodedata.normalize("NFKD", answer.casefold())
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    words_only = "".join(c if c.isalnum() else " " for c in without_accents)
    return " ".join(words_only.split())


def is_correct(given: str, expected: str) -> bool:
    given, expected = normalize(given), normalize(expected)
    if given == expected:
        return True
    return len(expected) >= TYPO_TOLERANCE_MIN_LENGTH and _one_edit_apart(given, expected)


def _one_edit_apart(a: str, b: str) -> bool:
    """True if one swapped, missing or extra character turns `a` into `b`."""
    if abs(len(a) - len(b)) > 1:
        return False
    shorter, longer = sorted((a, b), key=len)
    i = 0
    while i < len(shorter) and shorter[i] == longer[i]:
        i += 1
    if len(shorter) == len(longer):
        return shorter[i + 1 :] == longer[i + 1 :]
    return shorter[i:] == longer[i + 1 :]


def score(given: Sequence[str], expected: Sequence[str]) -> float:
    """Share of correct answers, from 0 to 1. Both lists follow the order of the questions."""
    if not expected:
        raise ValueError("a verification needs at least one question")
    if len(given) != len(expected):
        raise ValueError("a verification needs one answer per question")
    correct = sum(is_correct(g, e) for g, e in zip(given, expected, strict=True))
    return correct / len(expected)


def passes(value: float, min_score: float = MIN_SCORE) -> bool:
    return value >= min_score

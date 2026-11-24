"""Verificação de posse: nota das respostas do reivindicante."""

import unicodedata
from collections.abc import Sequence

# só aceita erro de digitação em resposta com 5 letras ou mais (nº de série tem que ser exato)
TYPO_TOLERANCE_MIN_LENGTH = 5
# abaixo disso rejeita direto, acima vai pro atendente
MIN_SCORE = 0.6


def normalize(answer: str) -> str:
    """Deixa minúsculo, tira acento, troca pontuação por espaço e junta espaços repetidos."""
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
    """True se `a` e `b` diferem em uma letra (trocada, faltando ou sobrando)."""
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
    """Fração de respostas certas (0 a 1). As listas estão na ordem das perguntas."""
    if not expected:
        raise ValueError("a verification needs at least one question")
    if len(given) != len(expected):
        raise ValueError("a verification needs one answer per question")
    correct = sum(is_correct(g, e) for g, e in zip(given, expected, strict=True))
    return correct / len(expected)


def passes(value: float, min_score: float = MIN_SCORE) -> bool:
    return value >= min_score

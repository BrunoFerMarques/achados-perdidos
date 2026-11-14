"""Match between a lost-item report and a found item (scope §8).
 Pure rules: no database, no framework. Scores are integers from 0 to 100,
so there is no float rounding to worry about when comparing with the cutoff.
""" 

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Protocol
from.verification import normalize

# words that say nothing about the object; already without accents, as `normalize` returns
STOPWORDS = frozenset(
    {
        "a", "as", "o", "os", "um", "uma", "uns", "umas",
        "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
        "com", "sem", "para", "por", "pra", "ao", "aos",
        "e", "ou", "que",
    }
)

# Read-only properties, so the SQLAlchemy model and a frozen dataclass in the 
# tests both fit these protocols (same idea as `Actor` in permissions.py).
class LostReportLike(Protocol):
    @property
    def category_id(self) -> int: ...
    @property
    def location_id(self) -> int: ...
    @property
    def color_id(self) -> int: ...
    @property
    def description(self) -> str: ...
    @property
    def lost_date(self) -> date: ...


class FoundItemLike(Protocol):
    @property
    def category_id(self) -> int: ...
    @property
    def location_id(self) -> int: ...
    @property
    def color_id(self) -> int: ...
    @property
    def description(self) -> str: ...
    @property
    def found_date(self) -> date: ...


# Defaults come from scope §8 and §12; injectable so tests can use their own values.
@dataclass(frozen=True)
class MatchConfig:
    min_score: int = 60
    max_days_before: int = 1  # found up to this many days before the loss still passes
    near_days_limit: int = 2  # found up to this many days after the loss: full date score
    mid_days_limit: int = 7  # found up to this many days after the loss: reduced date score
    weight_date_near: int = 30
    weight_date_mid: int = 15
    weight_location: int = 30
    weight_color: int = 20
    weight_description: int = 20

    @property
    def max_score(self) -> int:
        """Best possible score; with the defaults it is 100."""
        return (
            self.weight_date_near
            + self.weight_location
            + self.weight_color
            + self.weight_description
        )


# output
class RejectReason(str, Enum):
    CATEGORY_MISMATCH = "category_mismatch"
    FOUND_TOO_EARLY = "found_too_early"


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    score: int  # 0 to 100; always the sum of the four partial scores
    date_score: int = 0
    location_score: int = 0
    color_score: int = 0
    description_score: int = 0
    rejected_reason: RejectReason | None = None


# --- criteria ---
def normalize_tokens(text: str) -> frozenset[str]:
    """Words of a description: no accents, no punctuation, no stopwords."""
    return frozenset(w for w in normalize(text).split() if w not in STOPWORDS)


def score_description(text_a: str, text_b: str, weight: int) -> int:
    """Jaccard similarity of the two word sets times `weight`, rounded down.
    Integer division keeps the whole calculation in integers: 1 shared word
    out of 3 gives 20 * 1 // 3 = 6, never a float.
    """
    a, b = normalize_tokens(text_a), normalize_tokens(text_b)
    union = a | b
    if not union:  # both descriptions only had common words
        return 0
    return weight * len(a & b) // len(union)


def score_date(days_apart: int, config: MatchConfig) -> int:
    """`days_apart` is found date minus lost date; the early-found filter runs before this."""
    if days_apart <= config.near_days_limit:
        return config.weight_date_near
    if days_apart <= config.mid_days_limit:
        return config.weight_date_mid
    return 0


# match 
def _rejected(reason: RejectReason) -> MatchResult:
    return MatchResult(matched=False, score=0, rejected_reason=reason)


def calculate_match(
    report: LostReportLike,
    item: FoundItemLike,
    config: MatchConfig = MatchConfig(),  # frozen, so a shared default is safe
) -> MatchResult:
    """Compatibility between a lost-item report and an available item (scope §8)."""
    # filters: a pair that fails any of them is never scored
    if report.category_id != item.category_id:
        return _rejected(RejectReason.CATEGORY_MISMATCH)
    days_apart = (item.found_date - report.lost_date).days
    if days_apart < -config.max_days_before:
        return _rejected(RejectReason.FOUND_TOO_EARLY)

    # criteria: each one is scored on its own, the total is the sum
    date_points = score_date(days_apart, config)
    location_points = config.weight_location if report.location_id == item.location_id else 0
    color_points = config.weight_color if report.color_id == item.color_id else 0
    description_points = score_description(
        report.description, item.description, config.weight_description
    )

    total = date_points + location_points + color_points + description_points
    return MatchResult(
        matched=total >= config.min_score,
        score=total,
        date_score=date_points,
        location_score=location_points,
        color_score=color_points,
        description_score=description_points,
    )
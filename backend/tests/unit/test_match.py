from dataclasses import dataclass
from datetime import date, timedelta

import pytest

from domain.match import (
    MatchConfig,
    RejectReason,
    calculate_match,
    normalize_tokens,
    score_description,
)

LOST_ON = date(2026, 3, 10)


def at(days: int) -> date:
    """The date `days` after (or before, if negative) the loss."""
    return LOST_ON + timedelta(days=days)


# By default report and item are a perfect pair; each test changes only what it checks.
@dataclass(frozen=True)
class Report:
    category_id: int = 1
    location_id: int = 1
    color_id: int = 1
    description: str = "garrafa termica preta"
    lost_date: date = LOST_ON


@dataclass(frozen=True)
class Item:
    category_id: int = 1
    location_id: int = 1
    color_id: int = 1
    description: str = "garrafa termica preta"
    found_date: date = LOST_ON


# --- filters ---
def test_different_category_rejects_the_pair():  # §8 category filter
    result = calculate_match(Report(), Item(category_id=2))
    assert result.rejected_reason is RejectReason.CATEGORY_MISMATCH
    assert result.matched is False
    assert result.score == 0


def test_found_two_days_before_the_loss_rejects_the_pair():  # §8 date filter
    result = calculate_match(Report(), Item(found_date=at(-2)))
    assert result.rejected_reason is RejectReason.FOUND_TOO_EARLY
    assert result.matched is False
    assert result.score == 0


def test_found_one_day_before_the_loss_passes_with_full_date_score():  # §8 date edge
    result = calculate_match(Report(), Item(found_date=at(-1)))
    assert result.rejected_reason is None
    assert result.date_score == 30


# --- date score ---
@pytest.mark.parametrize(
    ("days_apart", "expected"),
    [(-1, 30), (0, 30), (1, 30), (2, 30), (3, 15), (7, 15), (8, 0), (60, 0)],
)
def test_date_score_by_days_between_loss_and_find(days_apart, expected):  # §8 date
    result = calculate_match(Report(), Item(found_date=at(days_apart)))
    assert result.date_score == expected


# --- location and color ---
def test_same_location_scores_30_and_different_scores_0():  # §8 location
    assert calculate_match(Report(), Item(location_id=1)).location_score == 30
    assert calculate_match(Report(), Item(location_id=2)).location_score == 0


def test_same_color_scores_20_and_different_scores_0():  # §8 color
    assert calculate_match(Report(), Item(color_id=1)).color_score == 20
    assert calculate_match(Report(), Item(color_id=2)).color_score == 0


# --- description ---
def test_tokens_drop_accents_case_punctuation_and_stopwords():  # §8 description
    assert normalize_tokens("Garrafa TÉRMICA, preta!") == {
        "garrafa",
        "termica",
        "preta",
    }
    assert normalize_tokens("bolsa de couro com alça") == {"bolsa", "couro", "alca"}


def test_description_score_for_the_example_in_the_scope():  # §8 example
    # {garrafa, preta} shared out of {garrafa, termica, preta, adesivo} = 0.5 * 20
    score = score_description("garrafa térmica preta", "garrafa preta com adesivo", 20)
    assert score == 10


def test_identical_descriptions_score_the_full_weight():
    assert score_description("mochila azul", "Mochila AZUL", 20) == 20


def test_descriptions_with_no_word_in_common_score_zero():
    assert score_description("mochila azul", "caderno verde", 20) == 0


def test_description_score_rounds_down():
    # 1 shared word out of 3 in total: 20 * 1 / 3 = 6.67 -> 6
    assert score_description("alfa beta", "alfa gama", 20) == 6


def test_descriptions_with_only_common_words_score_zero_instead_of_failing():
    assert score_description("de com", "o a", 20) == 0


# --- total and cutoff ---
def test_example_from_the_scope_scores_90_and_notifies():  # §8 example
    report = Report(description="garrafa térmica preta")
    item = Item(found_date=at(1), description="garrafa preta com adesivo")
    result = calculate_match(report, item)
    assert result.score == 90
    assert result.matched is True


def test_score_is_the_sum_of_the_partial_scores():  # §8 sum
    result = calculate_match(Report(), Item(found_date=at(5), color_id=2, description="garrafa"))
    parts = (
        result.date_score + result.location_score + result.color_score + result.description_score
    )
    assert result.score == parts


def test_default_weights_add_up_to_100_and_cutoff_is_60():  # §8 weights, §12
    config = MatchConfig()
    assert config.max_score == 100
    assert config.min_score == 60


def test_score_of_exactly_60_matches():  # §8 cutoff
    # date 30 + location 30, wrong color, no common word
    item = Item(color_id=2, description="caderno azul")
    result = calculate_match(Report(), item)
    assert result.score == 60
    assert result.matched is True


def test_score_of_59_does_not_match():  # §8 cutoff
    item = Item(color_id=2, description="caderno azul")
    result = calculate_match(Report(), item, MatchConfig(weight_location=29))
    assert result.score == 59
    assert result.matched is False

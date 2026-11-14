# scope §7 (docs/diagrama.md): ownership verification, scoring a claim's answers
import pytest

from domain.verification import is_correct, normalize, passes, score


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("AZUL", "azul"),
        ("Coração", "coracao"),
        ("banda queen!", "banda queen"),
        ("  banda   queen  ", "banda queen"),
        ("Azul-Céu", "azul ceu"),
    ],
)
def test_normalize_ignores_case_accents_punctuation_and_extra_spaces(answer, expected):
    assert normalize(answer) == expected


def test_normalize_treats_punctuation_as_a_separator():
    # "1,5" and "1.5" are the same answer; dropping the comma would glue the digits together
    assert normalize("1,5") == normalize("1.5") == "1 5"


def test_answer_equal_after_normalization_is_correct():
    assert is_correct("Banda Queen!", "banda queen")


def test_different_answer_is_wrong():
    assert not is_correct("verde", "azul")


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("pretu", "preto"),  # one letter swapped
        ("banda quen", "banda queen"),  # one letter missing
        ("banda queeen", "banda queen"),  # one letter too many
    ],
)
def test_one_typo_is_tolerated_when_the_expected_answer_has_5_or_more_characters(given, expected):
    assert is_correct(given, expected)


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("8F3B", "8F3A"),  # 4 characters: a serial number must be exact
        ("azu", "azul"),
        ("azuls", "azul"),  # the length that counts is the expected answer's
    ],
)
def test_no_typo_is_tolerated_when_the_expected_answer_has_less_than_5_characters(given, expected):
    assert not is_correct(given, expected)


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("bnda quen", "banda queen"),  # two letters missing
        ("prata", "preto"),  # two letters swapped
    ],
)
def test_two_typos_are_never_tolerated(given, expected):
    assert not is_correct(given, expected)


def answers(total: int, correct: int) -> tuple[list[str], list[str]]:
    """Answers to `total` questions, the first `correct` of them right."""
    expected = [f"resposta {i}" for i in range(total)]
    given = expected[:correct] + ["errada"] * (total - correct)
    return given, expected


def test_score_is_the_share_of_correct_answers():
    assert score(*answers(total=4, correct=1)) == 0.25


@pytest.mark.parametrize(
    ("total", "correct", "allowed"),
    [
        (2, 2, True),
        (2, 1, False),
        (3, 2, True),
        (3, 1, False),
        (4, 3, True),
        (4, 2, False),
        (5, 3, True),
        (5, 2, False),
    ],
)
def test_minimum_correct_answers_follow_the_table_in_section_7(total, correct, allowed):
    assert passes(score(*answers(total, correct))) is allowed


def test_score_of_exactly_60_percent_goes_to_review():
    assert passes(score(*answers(total=5, correct=3)))


def test_score_needs_one_answer_per_question():
    with pytest.raises(ValueError):
        score(["azul"], ["azul", "banda queen"])


def test_score_needs_at_least_one_question():
    with pytest.raises(ValueError):
        score([], [])

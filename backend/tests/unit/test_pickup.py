# código de retirada
import re
from datetime import UTC, datetime, timedelta

import pytest

from domain.claims import ClaimStatus
from domain.errors import (
    DocumentNotChecked,
    InvalidPickupCode,
    ItemNotAtThisPoint,
    PickupCodeAlreadyUsed,
    PickupCodeExpired,
)
from domain.pickup import (
    code_matches,
    complete_pickup,
    generate_code,
    normalize_code,
    pickup_deadline,
)

APPROVED_AT = datetime(2026, 11, 1, 12, tzinfo=UTC)
DEADLINE = APPROVED_AT + timedelta(days=5)
POINT = 1
OTHER_POINT = 2
CODE = "AB12CD"


def pickup(status: ClaimStatus = ClaimStatus.APPROVED, **overrides) -> ClaimStatus:
    """Uma retirada válida, a menos que o teste mude alguma coisa."""
    args = {
        "code": CODE,
        "typed_code": CODE,
        "deadline": DEADLINE,
        "item_point_id": POINT,
        "point_id": POINT,
        "document_checked": True,
        "now": APPROVED_AT + timedelta(days=1),
    }
    return complete_pickup(status, **(args | overrides))


def test_code_has_6_uppercase_letters_or_digits():
    for _ in range(100):
        assert re.fullmatch(r"[A-Z0-9]{6}", generate_code())


def test_codes_do_not_repeat():
    # 36^6 códigos possíveis: uma repetição em 100 quer dizer que o gerador está quebrado
    assert len({generate_code() for _ in range(100)}) == 100


@pytest.mark.parametrize("typed", ["ab12cd", " AB12CD ", "Ab12cD"])
def test_typed_code_ignores_case_and_surrounding_spaces(typed):
    assert normalize_code(typed) == "AB12CD"


def test_code_is_valid_for_5_days_after_approval():
    assert pickup_deadline(APPROVED_AT) == DEADLINE


def test_valid_pickup_completes_the_claim():
    assert pickup() == ClaimStatus.COMPLETED


@pytest.mark.parametrize("typed", ["ab12cd", " AB12CD ", "Ab12cD"])
def test_typed_code_matches_ignoring_case_and_surrounding_spaces(typed):
    assert code_matches(CODE, typed)


@pytest.mark.parametrize("typed", ["AB12CE", "AB12C", "", "ÁB12CD"])
def test_another_code_does_not_match(typed):
    # "Á" também: caractere não ASCII é só código errado, não pode quebrar
    assert not code_matches(CODE, typed)


def test_claim_without_a_code_matches_nothing():
    assert not code_matches(None, CODE)


def test_wrong_code_is_refused():
    with pytest.raises(InvalidPickupCode):
        pickup(typed_code="ZZZZZZ")


def test_wrong_code_does_not_tell_whether_the_claim_was_used():
    with pytest.raises(InvalidPickupCode):
        pickup(ClaimStatus.COMPLETED, typed_code="ZZZZZZ")


def test_code_is_single_use():
    # a primeira retirada conclui a reivindicação, então o código não serve de novo
    status = pickup()

    with pytest.raises(PickupCodeAlreadyUsed):
        pickup(status)


def test_code_still_works_just_before_the_deadline():
    assert pickup(now=DEADLINE - timedelta(seconds=1)) == ClaimStatus.COMPLETED


def test_code_expires_at_the_deadline():
    # mesmo que a tarefa agendada ainda não tenha marcado como expirada
    with pytest.raises(PickupCodeExpired):
        pickup(now=DEADLINE)


def test_code_of_an_expired_claim_is_refused():
    with pytest.raises(PickupCodeExpired):
        pickup(ClaimStatus.EXPIRED)


@pytest.mark.parametrize(
    "status", [ClaimStatus.PENDING, ClaimStatus.REJECTED, ClaimStatus.CANCELLED]
)
def test_claim_that_is_not_approved_has_no_valid_code(status):
    with pytest.raises(InvalidPickupCode):
        pickup(status)


def test_claim_that_was_never_approved_has_no_code_nor_deadline():
    with pytest.raises(InvalidPickupCode):
        pickup(ClaimStatus.PENDING, code=None, deadline=None)


def test_code_is_only_accepted_at_the_point_where_the_item_is():
    with pytest.raises(ItemNotAtThisPoint):
        pickup(point_id=OTHER_POINT)


def test_pickup_needs_the_photo_id_checked():
    with pytest.raises(DocumentNotChecked):
        pickup(document_checked=False)

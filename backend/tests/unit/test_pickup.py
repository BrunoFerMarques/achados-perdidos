# RN44 to RN46 (docs/diagrama.md §9): the pickup code
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
from domain.pickup import complete_pickup, generate_code, normalize_code, pickup_deadline

APPROVED_AT = datetime(2026, 11, 1, 12, tzinfo=UTC)
DEADLINE = APPROVED_AT + timedelta(days=5)
POINT = 1
OTHER_POINT = 2


def pickup(status: ClaimStatus = ClaimStatus.APPROVED, **overrides) -> ClaimStatus:
    """A valid pickup, unless the test overrides something."""
    args = {
        "deadline": DEADLINE,
        "item_point_id": POINT,
        "point_id": POINT,
        "document_checked": True,
        "now": APPROVED_AT + timedelta(days=1),
    }
    return complete_pickup(status, **(args | overrides))


def test_code_has_6_uppercase_letters_or_digits():
    # RN44
    for _ in range(100):
        assert re.fullmatch(r"[A-Z0-9]{6}", generate_code())


def test_codes_do_not_repeat():
    # 36^6 possible codes: a repeat in 100 would mean the generator is broken
    assert len({generate_code() for _ in range(100)}) == 100


@pytest.mark.parametrize("typed", ["ab12cd", " AB12CD ", "Ab12cD"])
def test_typed_code_ignores_case_and_surrounding_spaces(typed):
    assert normalize_code(typed) == "AB12CD"


def test_code_is_valid_for_5_days_after_approval():
    # RN44
    assert pickup_deadline(APPROVED_AT) == DEADLINE


def test_valid_pickup_completes_the_claim():
    assert pickup() == ClaimStatus.COMPLETED


def test_code_is_single_use():
    # RN44: the first pickup completes the claim, so the same code can't be used again
    status = pickup()

    with pytest.raises(PickupCodeAlreadyUsed):
        pickup(status)


def test_code_still_works_just_before_the_deadline():
    assert pickup(now=DEADLINE - timedelta(seconds=1)) == ClaimStatus.COMPLETED


def test_code_expires_at_the_deadline():
    # RN44: even if the scheduled task hasn't marked the claim as expired yet
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


def test_code_is_only_accepted_at_the_point_where_the_item_is():
    # RN45
    with pytest.raises(ItemNotAtThisPoint):
        pickup(point_id=OTHER_POINT)


def test_pickup_needs_the_photo_id_checked():
    # RN46
    with pytest.raises(DocumentNotChecked):
        pickup(document_checked=False)

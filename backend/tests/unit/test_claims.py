# scope §6 (docs/diagrama.md): claim lifecycle
from itertools import product

import pytest

from domain.claims import ClaimStatus, initial_status, is_active, transition
from domain.errors import InvalidTransition

ALLOWED = [
    (ClaimStatus.PENDING, ClaimStatus.APPROVED),  # attendant approves
    (ClaimStatus.PENDING, ClaimStatus.REJECTED),  # attendant rejects, or item returned to another
    (ClaimStatus.PENDING, ClaimStatus.CANCELLED),  # claimant cancels
    (ClaimStatus.APPROVED, ClaimStatus.COMPLETED),  # pickup validated
    (ClaimStatus.APPROVED, ClaimStatus.EXPIRED),  # pickup deadline passed
    (ClaimStatus.APPROVED, ClaimStatus.CANCELLED),  # claimant cancels
]
NOT_ALLOWED = [pair for pair in product(ClaimStatus, repeat=2) if pair not in ALLOWED]


@pytest.mark.parametrize(("current", "target"), ALLOWED)
def test_allowed_transition_returns_the_new_status(current, target):
    assert transition(current, target) == target


@pytest.mark.parametrize(("current", "target"), NOT_ALLOWED)
def test_any_other_transition_raises(current, target):
    with pytest.raises(InvalidTransition):
        transition(current, target)


def test_claim_that_passes_verification_starts_pending():
    assert initial_status(passed_verification=True) == ClaimStatus.PENDING


def test_claim_below_the_minimum_score_starts_rejected():
    assert initial_status(passed_verification=False) == ClaimStatus.REJECTED


@pytest.mark.parametrize(
    ("status", "active"),
    [
        (ClaimStatus.PENDING, True),
        (ClaimStatus.APPROVED, True),
        (ClaimStatus.REJECTED, False),
        (ClaimStatus.CANCELLED, False),
        (ClaimStatus.COMPLETED, False),
        (ClaimStatus.EXPIRED, False),
    ],
)
def test_only_pending_and_approved_claims_are_active(status, active):
    # RN11 and RN12 limit active claims
    assert is_active(status) is active

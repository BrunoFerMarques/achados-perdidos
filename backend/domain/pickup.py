"""Pickup code (RN44 to RN46): what the claimant shows at the collection point to take the item."""

import secrets
import string
from datetime import datetime, timedelta

from domain.claims import ClaimStatus, transition
from domain.errors import (
    DocumentNotChecked,
    InvalidPickupCode,
    ItemNotAtThisPoint,
    PickupCodeAlreadyUsed,
    PickupCodeExpired,
)

# scope §12
CODE_LENGTH = 6
PICKUP_WINDOW = timedelta(days=5)
ALPHABET = string.ascii_uppercase + string.digits


def generate_code() -> str:
    # secrets, not random: whoever guesses the code walks away with the item
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(code: str) -> str:
    # the attendant types what the claimant shows: case and stray spaces don't matter
    return code.strip().upper()


def pickup_deadline(approved_at: datetime) -> datetime:
    # RN44: the code is valid until the end of the pickup window, counted from the approval
    return approved_at + PICKUP_WINDOW


def code_matches(code: str | None, typed: str) -> bool:
    # bytes: compare_digest refuses str with non-ASCII characters, and the attendant types anything
    if code is None:
        return False
    return secrets.compare_digest(normalize_code(typed).encode(), code.encode())


def complete_pickup(
    status: ClaimStatus,
    *,
    code: str | None,
    typed_code: str,
    deadline: datetime | None,
    item_point_id: int,
    point_id: int,
    document_checked: bool,
    now: datetime,
) -> ClaimStatus:
    """Checks the pickup of a claim and returns its new status. `code` and `deadline` are None
    when the claim was never approved; `typed_code` is what the claimant showed at the counter;
    `point_id` is where the attendant is validating it; `now` comes from the caller, never from
    the system clock."""
    if not code_matches(code, typed_code):
        # first: a wrong code says nothing about the claim, not even whether it was used
        raise InvalidPickupCode()
    if status == ClaimStatus.COMPLETED:
        raise PickupCodeAlreadyUsed()  # RN44: single use
    if status == ClaimStatus.EXPIRED:
        raise PickupCodeExpired()
    if status != ClaimStatus.APPROVED or deadline is None:
        # a cancelled claim keeps its code in the database, but the code no longer opens anything
        raise InvalidPickupCode()
    if now >= deadline:
        raise PickupCodeExpired()  # the scheduled task may not have expired the claim yet
    if point_id != item_point_id:
        raise ItemNotAtThisPoint()  # RN45
    if not document_checked:
        raise DocumentNotChecked()  # RN46
    return transition(status, ClaimStatus.COMPLETED)

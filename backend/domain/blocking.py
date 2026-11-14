"""Blocking a user from claiming after too many failed claims (RN15, RN16)."""

from collections.abc import Iterable
from datetime import datetime, timedelta

from domain.claims import RejectionReason

# scope §12
FAILURES_TO_BLOCK = 3
FAILURE_WINDOW = timedelta(days=30)
BLOCK_DURATION = timedelta(days=7)


def counts_as_failure(reason: RejectionReason) -> bool:
    # cancelled and expired claims aren't rejections, so they never get here
    return reason != RejectionReason.ITEM_RETURNED


def is_blocked(
    failures: Iterable[datetime], now: datetime, unblocked_at: datetime | None = None
) -> bool:
    """`failures` are when the user's failed claims were rejected; `unblocked_at` is the last
    time an admin lifted a block. `now` comes from the caller, never from the system clock."""
    end = _block_end(failures, unblocked_at)
    return end is not None and now < end


def _block_end(failures: Iterable[datetime], unblocked_at: datetime | None) -> datetime | None:
    counted: list[datetime] = []
    end = None
    for failure in sorted(failures):
        if unblocked_at is not None and failure <= unblocked_at:
            continue  # RN16: the admin wiped the slate
        counted = [f for f in counted if failure - f < FAILURE_WINDOW]
        counted.append(failure)
        if len(counted) >= FAILURES_TO_BLOCK:
            end = failure + BLOCK_DURATION
            counted = []  # these failures were paid for with a block; they won't block again
    return end

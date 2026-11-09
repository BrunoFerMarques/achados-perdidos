# RN15 and RN16 (docs/diagrama.md §6): blocking a user after failed claims
from datetime import UTC, datetime, timedelta

import pytest

from domain.blocking import counts_as_failure, is_blocked
from domain.claims import RejectionReason

START = datetime(2026, 11, 1, 12, tzinfo=UTC)


def day(n: float) -> datetime:
    return START + timedelta(days=n)


@pytest.mark.parametrize("reason", [RejectionReason.LOW_SCORE, RejectionReason.ATTENDANT])
def test_rejection_by_score_or_by_attendant_counts_as_failure(reason):
    assert counts_as_failure(reason)


def test_rejection_because_item_was_returned_to_someone_else_does_not_count():
    # RN14: the claimant did nothing wrong, the item just went to its owner first
    assert not counts_as_failure(RejectionReason.ITEM_RETURNED)


def test_three_failures_within_30_days_block_the_user():
    assert is_blocked([day(0), day(10), day(20)], now=day(21))


def test_two_failures_do_not_block():
    assert not is_blocked([day(0), day(10)], now=day(11))


def test_a_failure_older_than_30_days_no_longer_counts():
    assert not is_blocked([day(0), day(15), day(31)], now=day(32))


def test_user_is_still_blocked_6_days_after_the_third_failure():
    assert is_blocked([day(0), day(1), day(2)], now=day(2 + 6))


def test_block_ends_7_days_after_the_third_failure():
    assert not is_blocked([day(0), day(1), day(2)], now=day(2 + 7))


def test_failures_that_caused_a_block_do_not_count_again_after_it_ends():
    # otherwise one more failure on day 10 would block again, with failures already paid for
    assert not is_blocked([day(0), day(1), day(2), day(10)], now=day(11))


def test_three_new_failures_after_a_block_block_again():
    assert is_blocked([day(0), day(1), day(2), day(10), day(11), day(12)], now=day(13))


def test_admin_unblock_frees_the_user_at_once():
    # RN16
    assert not is_blocked([day(0), day(1), day(2)], now=day(3), unblocked_at=day(2.5))


def test_failures_after_an_admin_unblock_still_count():
    failures = [day(0), day(1), day(2), day(3), day(4), day(5)]
    assert is_blocked(failures, now=day(6), unblocked_at=day(2.5))

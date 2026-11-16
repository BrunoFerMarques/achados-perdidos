from datetime import UTC

from domain.clock import SystemClock


def test_system_clock_is_timezone_aware():
    # the dates it gives are compared with TIMESTAMPTZ columns; a naive datetime can't be
    assert SystemClock().now().tzinfo is UTC

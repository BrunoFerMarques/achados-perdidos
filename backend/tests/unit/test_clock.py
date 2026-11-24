from datetime import UTC

from domain.clock import SystemClock


def test_system_clock_is_timezone_aware():
    # as datas são comparadas com colunas TIMESTAMPTZ, o que um datetime sem fuso não permite
    assert SystemClock().now().tzinfo is UTC

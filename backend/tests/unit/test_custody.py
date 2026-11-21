from domain.custody import EVENTS
from domain.items import TRANSITIONS

ARROWS = {(current, target) for current, targets in TRANSITIONS.items() for target in targets}


def test_every_arrow_has_an_event():  # RN06
    assert set(EVENTS) == ARROWS

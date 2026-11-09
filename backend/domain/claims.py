"""Claims (scope §6): someone saying a found item is theirs."""

from enum import StrEnum


class RejectionReason(StrEnum):
    LOW_SCORE = "nota_baixa"  # below the minimum verification score, rejected at once
    ATTENDANT = "atendente"  # the attendant reviewed it and said no
    ITEM_RETURNED = "item_devolvido"  # RN14: the item went to someone else

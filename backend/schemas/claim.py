from datetime import datetime
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from domain.claims import ClaimStatus
from domain.items import MAX_QUESTIONS, MIN_QUESTIONS
from domain.pickup import CODE_LENGTH

# blank is allowed: "I don't know" is an answer, it just doesn't score
Answer = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class ClaimCreate(BaseModel):
    item_id: int
    # one answer per question, in the order the item lists them
    answers: Annotated[list[Answer], Field(min_length=MIN_QUESTIONS, max_length=MAX_QUESTIONS)]


class ClaimOut(BaseModel):
    """What the claimant sees (RN21, RN53): status, collection point and pickup code. No score,
    no rejection reason and no expected answer (RN23)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    status: str
    collection_point_id: int
    pickup_code: str | None
    pickup_deadline: datetime | None
    created_at: datetime

    @model_validator(mode="after")
    def _code_only_while_approved(self) -> Self:
        # a cancelled, expired or completed claim keeps the code in the database, but it no
        # longer opens anything (RN44)
        if self.status != ClaimStatus.APPROVED:
            self.pickup_code = None
            self.pickup_deadline = None
        return self


class ReviewedAnswerOut(BaseModel):
    position: int
    question: str
    expected: str
    given: str


class ClaimReviewOut(BaseModel):
    """What the attendant sees (RN22): the score and each answer next to the expected one. No
    pickup code: the claimant shows it at the counter, so whoever validates it never reads it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    claimant_id: int
    status: str
    score: float
    collection_point_id: int
    created_at: datetime
    answers: list[ReviewedAnswerOut]

    @model_validator(mode="before")
    @classmethod
    def _pair_answers(cls, claim: Any) -> Any:
        # built from the Claim model: each given answer meets its question by position
        if isinstance(claim, dict):
            return claim
        questions = {q.position: q for q in claim.item.questions}
        fields = {name: getattr(claim, name) for name in cls.model_fields if name != "answers"}
        fields["answers"] = [
            ReviewedAnswerOut(
                position=a.position,
                question=questions[a.position].question,
                expected=questions[a.position].answer,
                given=a.answer,
            )
            for a in claim.answers
        ]
        return fields


# a code of another length can't be right; the domain decides about the rest (RN44)
PickupCode = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=CODE_LENGTH, max_length=CODE_LENGTH)
]


class PickupIn(BaseModel):
    """What the attendant fills in at the counter (RN44 to RN46)."""

    # the counter where the claimant showed up; RN45 wants it to be where the item is
    collection_point_id: int
    # typed from what the claimant shows; case and stray spaces don't matter
    pickup_code: PickupCode
    # RN46: no default, the attendant ticks it on purpose
    document_checked: bool


class ClaimPickupOut(BaseModel):
    """What the attendant sees at the counter: who comes for which item, and until when. The name
    is for the photo ID check (RN46). No pickup code: the claimant shows it, like in the review."""

    id: int
    item_id: int
    item_description: str
    claimant_id: int
    claimant_name: str
    status: str
    collection_point_id: int
    pickup_deadline: datetime | None

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, claim: Any) -> Any:
        # built from the Claim model: the description and the name come from its relationships
        if isinstance(claim, dict):
            return claim
        return {
            "id": claim.id,
            "item_id": claim.item_id,
            "item_description": claim.item.description,
            "claimant_id": claim.claimant_id,
            "claimant_name": claim.claimant.name,
            "status": claim.status,
            "collection_point_id": claim.collection_point_id,
            "pickup_deadline": claim.pickup_deadline,
        }

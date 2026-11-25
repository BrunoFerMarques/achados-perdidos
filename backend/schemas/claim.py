from datetime import datetime
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from domain.claims import ClaimStatus
from domain.items import MAX_QUESTIONS, MIN_QUESTIONS
from domain.pickup import CODE_LENGTH

# pode ficar em branco ("não sei" também é resposta, só não pontua)
Answer = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class ClaimCreate(BaseModel):
    item_id: int
    # uma resposta por pergunta, na mesma ordem das perguntas do item
    answers: Annotated[list[Answer], Field(min_length=MIN_QUESTIONS, max_length=MAX_QUESTIONS)]


class ClaimOut(BaseModel):
    """O que o reivindicante vê: status, ponto de coleta e código de retirada. Nada de nota,
    motivo da rejeição ou resposta esperada."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    # a que qualquer um já lê no mural, pra ele saber qual é o item
    item_public_description: str
    status: str
    collection_point_id: int
    pickup_code: str | None
    pickup_deadline: datetime | None
    created_at: datetime

    @model_validator(mode="after")
    def _code_only_while_approved(self) -> Self:
        # cancelada, expirada ou concluída ainda tem o código salvo, mas ele não vale mais
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
    """O que o atendente vê na análise: a nota e cada resposta do lado da esperada. Não tem o
    código de retirada, quem mostra o código é o reivindicante no balcão."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    item_description: str
    claimant_id: int
    status: str
    score: float
    collection_point_id: int
    created_at: datetime
    answers: list[ReviewedAnswerOut]

    @model_validator(mode="before")
    @classmethod
    def _pair_answers(cls, claim: Any) -> Any:
        # monta a partir do Claim, juntando cada resposta com a pergunta pela posição
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


# código com outro tamanho já está errado; o resto o domínio confere
PickupCode = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=CODE_LENGTH, max_length=CODE_LENGTH)
]


class PickupIn(BaseModel):
    """O que o atendente preenche no balcão."""

    # balcão onde a pessoa apareceu, tem que ser o ponto onde o item está
    collection_point_id: int
    # digitado a partir do que a pessoa mostra, maiúsculas e espaços não importam
    pickup_code: PickupCode
    # sem valor padrão de propósito: o atendente tem que marcar
    document_checked: bool


class ClaimPickupOut(BaseModel):
    """O que o atendente vê no balcão: quem vem buscar qual item e até quando. O nome é pra
    conferir o documento. Não tem o código, quem mostra é a pessoa."""

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
        # monta a partir do Claim, pegando descrição e nome das relações
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

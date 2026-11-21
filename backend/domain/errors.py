class DomainError(Exception):
    """A business rule refused the operation. The message is shown to the API client."""

    message = "Operação não permitida"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)


class NotFoundError(DomainError):
    """The requested record doesn't exist."""


class ConflictError(DomainError):
    """The operation clashes with data that already exists."""


class UnauthorizedError(DomainError):
    """The client didn't prove who it is."""


class ForbiddenError(DomainError):
    """The client proved who it is, but may not do this."""


class InvalidRequestError(DomainError):
    """The request is well formed, but doesn't fit the record it points at."""


class InvalidCredentials(UnauthorizedError):
    message = "E-mail ou senha inválidos"


class NotAuthenticated(UnauthorizedError):
    message = "Não autenticado"


class InvalidToken(UnauthorizedError):
    message = "Token inválido ou expirado"


class PermissionDenied(ForbiddenError):
    message = "Sem permissão para esta operação"


class UserNotFound(NotFoundError):
    message = "Usuário não encontrado"


class EmailAlreadyExists(ConflictError):
    message = "E-mail já cadastrado"


class InvalidTransition(ConflictError):
    message = "Mudança de estado não permitida"


class CollectionPointNotFound(NotFoundError):
    message = "Ponto de coleta não encontrado"


class AttendantLinkNotFound(NotFoundError):
    message = "Atendente não vinculado a este ponto"


class CollectionPointNameExists(ConflictError):
    message = "Já existe um ponto de coleta com este nome"


class AttendantAlreadyLinked(ConflictError):
    message = "Atendente já vinculado a este ponto"


class UserIsNotAttendant(ConflictError):
    message = "O usuário não é atendente"


class InvalidPickupCode(InvalidRequestError):
    # 422, not 404: the claim exists, the code typed for it doesn't fit
    message = "Código de retirada inválido"


class PickupCodeAlreadyUsed(ConflictError):
    message = "Código de retirada já usado"


class PickupCodeExpired(ConflictError):
    message = "Código de retirada vencido"


class ItemNotAtThisPoint(ConflictError):
    message = "O item não está neste ponto de coleta"


class DocumentNotChecked(ConflictError):
    message = "Confira o documento com foto antes de concluir a retirada"


class ItemNotFound(NotFoundError):
    message = "Item não encontrado"


class ClaimNotFound(NotFoundError):
    message = "Reivindicação não encontrada"


class OwnItemClaim(ForbiddenError):
    message = "Você não pode reivindicar um item que registrou"


class ClaimingBlocked(ForbiddenError):
    message = "Você está temporariamente bloqueado de reivindicar itens"


class ItemNotClaimable(ConflictError):
    message = "Este item não aceita reivindicações"


class ItemAlreadyClaimed(ConflictError):
    message = "Você já reivindicou este item"


class TooManyActiveClaims(ConflictError):
    message = "Você atingiu o limite de reivindicações ativas"


class ItemNotAvailable(ConflictError):
    message = "O item não está disponível"


class WrongAnswerCount(InvalidRequestError):
    message = "Responda todas as perguntas do item"


class CategoryNotFound(NotFoundError):
    message = "Categoria não encontrada"


class LocationNotFound(NotFoundError):
    message = "Local não encontrado"


class ColorNotFound(NotFoundError):
    message = "Cor não encontrada"

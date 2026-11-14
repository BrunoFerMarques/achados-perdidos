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

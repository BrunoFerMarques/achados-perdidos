class DomainError(Exception):
    """A business rule refused the operation. The message is shown to the API client."""

    message = "Operação não permitida"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)


class NotFoundError(DomainError):
    """The requested record doesn't exist."""


class ConflictError(DomainError):
    """The operation clashes with data that already exists."""


class UserNotFound(NotFoundError):
    message = "Usuário não encontrado"


class EmailAlreadyExists(ConflictError):
    message = "E-mail já cadastrado"

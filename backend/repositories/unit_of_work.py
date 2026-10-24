from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.errors import ConflictError, EmailAlreadyExists
from repositories.user import UserRepository

# unique constraints whose violation is a business error, not a bug
CONFLICTS: dict[str, type[ConflictError]] = {
    "users_email_key": EmailAlreadyExists,
}


class UnitOfWork:
    """One business transaction: every repository shares the session and commit saves it all."""

    def __init__(self, session: Session):
        self._session = session
        self.users = UserRepository(session)

    def commit(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            conflict = CONFLICTS.get(error.orig.diag.constraint_name)
            if conflict is None:
                raise
            raise conflict() from None

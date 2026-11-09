from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from db import SessionDep
from domain.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from routers import auth, categories, colors, locations, users

load_dotenv()

app = FastAPI(title="Achados e Perdidos API")
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(locations.router)
app.include_router(colors.router)


def _error_response(status_code: int, headers: dict[str, str] | None = None):
    def handler(request: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=status_code, content={"detail": str(error)}, headers=headers
        )

    return handler


# business errors become HTTP responses only here, so services never know about HTTP
app.add_exception_handler(NotFoundError, _error_response(404))
app.add_exception_handler(ConflictError, _error_response(409))
# the HTTP spec asks a 401 to say which scheme to authenticate with
app.add_exception_handler(UnauthorizedError, _error_response(401, {"WWW-Authenticate": "Bearer"}))
# logged in, but not allowed: 403, so the client knows logging in again won't help
app.add_exception_handler(ForbiddenError, _error_response(403))


@app.get("/")
def raiz():
    return {"mensagem": "API Achados e Perdidos no ar"}


@app.get("/health")
def health(session: SessionDep):
    # an unreachable database was already answered with 503 by get_session
    session.execute(select(1))
    return {"status": "ok", "banco": "ok"}

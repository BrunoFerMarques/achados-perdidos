import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from db import SessionDep
from domain.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    InvalidRequestError,
    NotFoundError,
    UnauthorizedError,
)
from routers import (
    auth,
    categories,
    claims,
    collection_points,
    colors,
    items,
    locations,
    lost_reports,
    notifications,
    users,
)

load_dotenv()

app = FastAPI(title="Achados e Perdidos API")
# the browser only lets the frontend read our answers if its origin is on this list
origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins.split(",")],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(locations.router)
app.include_router(colors.router)
app.include_router(collection_points.router)
app.include_router(lost_reports.router)
app.include_router(notifications.router)
app.include_router(items.router)
app.include_router(claims.router)


def _error_response(status_code: int, headers: dict[str, str] | None = None):
    def handler(request: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=status_code, content={"detail": str(error)}, headers=headers
        )

    return handler


# os erros de negócio só viram resposta HTTP aqui, os services não sabem nada de HTTP
app.add_exception_handler(NotFoundError, _error_response(404))
app.add_exception_handler(ConflictError, _error_response(409))
# o HTTP pede que o 401 diga qual esquema de autenticação usar
app.add_exception_handler(UnauthorizedError, _error_response(401, {"WWW-Authenticate": "Bearer"}))
# 403: está logado mas não pode, então logar de novo não resolve
app.add_exception_handler(ForbiddenError, _error_response(403))
# 422: o corpo é válido, mas não bate com o registro (ex.: 2 respostas num item com 3 perguntas)
app.add_exception_handler(InvalidRequestError, _error_response(422))


@app.get("/")
def raiz():
    return {"mensagem": "API Achados e Perdidos no ar"}


@app.get("/health")
def health(session: SessionDep):
    # banco fora do ar já virou 503 no get_session
    session.execute(select(1))
    return {"status": "ok", "banco": "ok"}

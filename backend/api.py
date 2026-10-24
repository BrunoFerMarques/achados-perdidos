from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from db import SessionDep
from domain.errors import ConflictError, DomainError, NotFoundError
from routers import users

load_dotenv()

app = FastAPI(title="Achados e Perdidos API")
app.include_router(users.router)


def _error_response(status_code: int):
    def handler(request: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(error)})

    return handler


# business errors become HTTP responses only here, so services never know about HTTP
app.add_exception_handler(NotFoundError, _error_response(404))
app.add_exception_handler(ConflictError, _error_response(409))


@app.get("/")
def raiz():
    return {"mensagem": "API Achados e Perdidos no ar"}


@app.get("/health")
def health(session: SessionDep):
    # an unreachable database was already answered with 503 by get_session
    session.execute(select(1))
    return {"status": "ok", "banco": "ok"}

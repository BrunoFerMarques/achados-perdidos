from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy import select

from db import SessionDep
from routers import users

load_dotenv()

app = FastAPI(title="Achados e Perdidos API")
app.include_router(users.router)


@app.get("/")
def raiz():
    return {"mensagem": "API Achados e Perdidos no ar"}


@app.get("/health")
def health(session: SessionDep):
    # an unreachable database was already answered with 503 by get_session
    session.execute(select(1))
    return {"status": "ok", "banco": "ok"}

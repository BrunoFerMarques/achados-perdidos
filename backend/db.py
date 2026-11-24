import os
from functools import cache
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import URL, Engine, create_engine, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


def database_url() -> URL:
    # o Neon fornece postgresql://, mas o SQLAlchemy precisa do nome do driver na URL
    return make_url(os.environ["DATABASE_URL"]).set(drivername="postgresql+psycopg")


@cache
def _engine(url: URL) -> Engine:
    # o Neon derruba conexão parada, então testa antes de usar (pre-ping)
    return create_engine(url, connect_args={"connect_timeout": 10}, pool_pre_ping=True)


def get_engine() -> Engine:
    # lê a variável toda vez porque nos testes ela aponta pra outro banco
    return _engine(database_url())


def get_session():
    # a resposta é montada depois do commit, então os objetos não podem expirar
    with Session(get_engine(), expire_on_commit=False) as session:
        try:
            # conecta logo pra devolver 503 antes da rota rodar se o banco estiver fora
            session.connection()
        except OperationalError:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível") from None
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

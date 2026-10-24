import os
from functools import cache
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import URL, Engine, create_engine, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


def database_url() -> URL:
    # DATABASE_URL keeps the plain postgresql:// form Neon gives; SQLAlchemy needs the driver named
    return make_url(os.environ["DATABASE_URL"]).set(drivername="postgresql+psycopg")


@cache
def _engine(url: URL) -> Engine:
    # pre-ping: Neon drops idle connections, so check one before handing it out
    return create_engine(url, connect_args={"connect_timeout": 10}, pool_pre_ping=True)


def get_engine() -> Engine:
    # DATABASE_URL is read on every call; during tests it is pointed at another database
    return _engine(database_url())


def get_session():
    # expire_on_commit=False: the response is built from the objects after the commit
    with Session(get_engine(), expire_on_commit=False) as session:
        try:
            # connect up front, so an unreachable database is a 503 before the route runs
            session.connection()
        except OperationalError:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível") from None
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

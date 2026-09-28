import os

import psycopg
from fastapi import HTTPException
from psycopg.rows import dict_row


def get_conn():
    try:
        conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=10, row_factory=dict_row)
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="Banco de dados indisponível") from None
    with conn:
        yield conn

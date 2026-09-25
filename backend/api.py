import os

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from routers import users

load_dotenv()

app = FastAPI(title="Achados e Perdidos API")
app.include_router(users.router)


@app.get("/")
def raiz():
    return {"mensagem": "API Achados e Perdidos no ar"}


@app.get("/health")
def health():
    try:
        with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=10) as conn:
            conn.execute("SELECT 1")
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="Banco de dados indisponível")
    return {"status": "ok", "banco": "ok"}

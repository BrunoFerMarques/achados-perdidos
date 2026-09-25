import os

import psycopg
from psycopg.rows import dict_row


def get_conn():
    # autocommit: each write that needs atomicity opens its own conn.transaction()
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True, row_factory=dict_row) as conn:
        yield conn

from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from db import database_url
from models import Base

config = context.config

if config.config_file_name is not None:
    # keep the loggers pytest and uvicorn have already set up
    fileConfig(config.config_file_name, disable_existing_loggers=False)

load_dotenv()

# one transaction per migration: a failing migration leaves nothing behind
OPTIONS = {"target_metadata": Base.metadata, "transaction_per_migration": True}


def run_migrations_offline() -> None:
    # `alembic upgrade head --sql` prints the SQL instead of running it
    context.configure(url=database_url(), literal_binds=True, **OPTIONS)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, **OPTIONS)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

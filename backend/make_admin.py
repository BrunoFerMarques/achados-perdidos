"""Dá o papel de admin pra uma conta que já existe.

Uso: python make_admin.py <email>   (a pessoa precisa se cadastrar pela API antes)

A API não deixa ninguém virar admin sozinho: o cadastro sempre cria usuario e só admin muda
papel. Por isso o primeiro admin é criado aqui, por quem tem acesso ao banco.
"""

import sys

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from db import get_engine
from dependencies import get_clock, get_user_service
from domain.errors import UserNotFound
from repositories.unit_of_work import UnitOfWork

USAGE = "Uso: python make_admin.py <email>"


def main(args: list[str]) -> int:
    if len(args) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    load_dotenv()
    with Session(get_engine(), expire_on_commit=False) as session:
        # usa a mesma composition root da API, então roda o mesmo caso de uso
        users = get_user_service(UnitOfWork(session), get_clock())
        try:
            user = users.promote_to_admin(args[0])
        except UserNotFound as error:
            print(error, file=sys.stderr)
            return 1
    print(f"{user.email} agora é admin")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

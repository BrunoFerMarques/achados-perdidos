"""Give the admin role to an account that already exists.

Usage: python make_admin.py <email>   (the person registers through the API first)

The API never makes anyone admin on its own: registering always gives the usuario role, and only
an admin can change roles. So the first admin is made here, by someone with access to DATABASE_URL.
"""

import sys

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from db import get_engine
from dependencies import get_user_service
from domain.errors import UserNotFound
from repositories.unit_of_work import UnitOfWork

USAGE = "Uso: python make_admin.py <email>"


def main(args: list[str]) -> int:
    if len(args) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    load_dotenv()
    with Session(get_engine(), expire_on_commit=False) as session:
        # built by the same composition root as the API, so the script runs the same use case
        users = get_user_service(UnitOfWork(session))
        try:
            user = users.promote_to_admin(args[0])
        except UserNotFound as error:
            print(error, file=sys.stderr)
            return 1
    print(f"{user.email} agora é admin")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

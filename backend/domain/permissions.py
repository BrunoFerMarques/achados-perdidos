"""Who may do what (scope §11). Each rule only answers yes or no; `ensure` turns a no into 403.

The rules live here, not in the routers, so they hold for every way into a service and can be
tested without a database or a server.
"""

from typing import Protocol

from domain.errors import PermissionDenied
from domain.roles import Role


class Actor(Protocol):
    """Whoever is asking. The User model fits it as is, so domain/ doesn't import models/."""

    id: int
    role: str


def ensure(allowed: bool) -> None:
    if not allowed:
        raise PermissionDenied()


def can_list_users(actor: Actor) -> bool:
    return actor.role == Role.ADMIN


def can_manage_user(actor: Actor, user_id: int) -> bool:
    # see, edit and delete an account: your own, or anyone's if you are an admin
    return actor.role == Role.ADMIN or actor.id == user_id


def can_change_role(actor: Actor, user_id: int) -> bool:
    # not your own: an admin can't take away their own access by mistake
    return actor.role == Role.ADMIN and actor.id != user_id


def can_manage_collection_points(actor: Actor) -> bool:
    # RN40: only an admin registers collection points and links attendants
    return actor.role == Role.ADMIN
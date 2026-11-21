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


def can_unblock_user(actor: Actor) -> bool:
    # RN16: only an admin lifts a block before it ends
    return actor.role == Role.ADMIN


def can_claim(actor: Actor) -> bool:
    # scope §11: users claim items; attendants and admins are the ones who review the claims
    return actor.role == Role.USUARIO


def can_cancel_claim(actor: Actor, claimant_id: int) -> bool:
    return actor.id == claimant_id


def can_review_claims(actor: Actor) -> bool:
    return actor.role in (Role.ATENDENTE, Role.ADMIN)


def operates_every_point(actor: Actor) -> bool:
    return actor.role == Role.ADMIN


def can_operate_item(actor: Actor, item_point_id: int, actor_point_ids: set[int]) -> bool:
    # RN41: an attendant only handles items at the points they work at; an admin, at any point
    if operates_every_point(actor):
        return True
    return actor.role == Role.ATENDENTE and item_point_id in actor_point_ids


def can_review_claim(
    actor: Actor, claimant_id: int, item_point_id: int, actor_point_ids: set[int]
) -> bool:
    # nobody reviews or hands over their own claim: a user who claimed and was later made an
    # attendant (RN21)
    return (
        can_review_claims(actor)
        and actor.id != claimant_id
        and can_operate_item(actor, item_point_id, actor_point_ids)
    )


def can_view_custody(actor: Actor) -> bool:
    # RN53: the finder and the claimant only follow the status; the history is for the staff
    return actor.role in (Role.ATENDENTE, Role.ADMIN)


def can_manage_collection_points(actor: Actor) -> bool:
    # RN40: only an admin registers collection points and links attendants
    return actor.role == Role.ADMIN


def can_create_lost_report(actor: Actor) -> bool:
    # scope §11: only regular users report lost items
    return actor.role == Role.USUARIO


def can_list_lost_reports(actor: Actor) -> bool:
    # scope §11: only regular users have reports to list
    return actor.role == Role.USUARIO


def can_access_lost_report(actor: Actor, owner_id: int) -> bool:
    # design decision: the scope is silent on who may view or close a report,
    # so only the owner can
    return actor.role == Role.USUARIO and actor.id == owner_id

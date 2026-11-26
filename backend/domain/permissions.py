"""Regras de permissão.

Cada função só responde True ou False, e o `ensure` transforma o False em 403. Ficam aqui e não
nos routers pra valer em qualquer entrada e dar pra testar sem banco.
"""

from typing import Protocol

from domain.errors import PermissionDenied
from domain.roles import Role


class Actor(Protocol):
    """Quem está fazendo o pedido. O User já encaixa aqui sem o domain/ importar models/."""

    id: int
    role: str


def ensure(allowed: bool) -> None:
    if not allowed:
        raise PermissionDenied()


def can_list_users(actor: Actor) -> bool:
    return actor.role == Role.ADMIN


def can_manage_user(actor: Actor, user_id: int) -> bool:
    # a própria conta, ou qualquer uma se for admin
    return actor.role == Role.ADMIN or actor.id == user_id


def can_change_role(actor: Actor, user_id: int) -> bool:
    # nem o admin muda o próprio papel, pra não se trancar fora sem querer
    return actor.role == Role.ADMIN and actor.id != user_id


def can_unblock_user(actor: Actor) -> bool:
    # só o admin desbloqueia
    return actor.role == Role.ADMIN


def can_claim(actor: Actor) -> bool:
    # quem reivindica é usuário; atendente e admin só analisam
    return actor.role == Role.USUARIO


def can_cancel_claim(actor: Actor, claimant_id: int) -> bool:
    return actor.id == claimant_id


def can_review_claims(actor: Actor) -> bool:
    return actor.role in (Role.ATENDENTE, Role.ADMIN)


def operates_every_point(actor: Actor) -> bool:
    return actor.role == Role.ADMIN


def can_operate_item(actor: Actor, item_point_id: int, actor_point_ids: set[int]) -> bool:
    # atendente só mexe em item dos pontos dele, admin em qualquer um
    if operates_every_point(actor):
        return True
    return actor.role == Role.ATENDENTE and item_point_id in actor_point_ids


def can_review_claim(
    actor: Actor, claimant_id: int, item_point_id: int, actor_point_ids: set[int]
) -> bool:
    # ninguém analisa a própria reivindicação (ex.: usuário que virou atendente depois)
    return (
        can_review_claims(actor)
        and actor.id != claimant_id
        and can_operate_item(actor, item_point_id, actor_point_ids)
    )


def can_view_custody(actor: Actor) -> bool:
    # RN53: the finder and the claimant only follow the status; the history is for the staff
    return actor.role in (Role.ATENDENTE, Role.ADMIN)


def can_transfer_items(actor: Actor) -> bool:
    # só a equipe transfere, e só itens dos próprios pontos
    return actor.role in (Role.ATENDENTE, Role.ADMIN)


def can_receive_items(actor: Actor) -> bool:
    # RN02: any attendant may receive any registered item; RN41 then checks the counter
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


def can_use_notifications(actor: Actor) -> bool:
    return actor.role == Role.USUARIO

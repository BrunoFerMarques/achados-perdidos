from datetime import timedelta

import jwt
import pytest

from domain.errors import InvalidToken
from services.token import TokenService

SECRET = "secret-only-for-the-token-service-tests"


def test_issued_token_carries_the_user_id():
    tokens = TokenService(SECRET, timedelta(hours=1))

    assert tokens.user_id(tokens.issue(7)) == 7


def test_expired_token_is_rejected():
    tokens = TokenService(SECRET, timedelta(seconds=-1))

    with pytest.raises(InvalidToken):
        tokens.user_id(tokens.issue(7))


def test_token_signed_with_another_secret_is_rejected():
    token = TokenService("another-secret-that-is-also-long-enough", timedelta(hours=1)).issue(7)

    with pytest.raises(InvalidToken):
        TokenService(SECRET, timedelta(hours=1)).user_id(token)


def test_token_without_expiration_is_rejected():
    token = jwt.encode({"sub": "7"}, SECRET, algorithm="HS256")

    with pytest.raises(InvalidToken):
        TokenService(SECRET, timedelta(hours=1)).user_id(token)


def test_malformed_token_is_rejected():
    with pytest.raises(InvalidToken):
        TokenService(SECRET, timedelta(hours=1)).user_id("nao-e-um-jwt")

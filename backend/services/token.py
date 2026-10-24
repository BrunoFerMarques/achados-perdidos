from datetime import UTC, datetime, timedelta

import jwt

from domain.errors import InvalidToken


class TokenService:
    """Signs the access tokens (JWT) handed out at login and reads them back."""

    algorithm = "HS256"

    def __init__(self, secret: str, ttl: timedelta):
        self._secret = secret
        self._ttl = ttl

    def issue(self, user_id: int) -> str:
        now = datetime.now(UTC)
        # the JWT spec requires sub to be a string
        claims = {"sub": str(user_id), "iat": now, "exp": now + self._ttl}
        return jwt.encode(claims, self._secret, algorithm=self.algorithm)

    def user_id(self, token: str) -> int:
        try:
            # decode checks the signature and exp; requiring exp refuses a token that never expires
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[self.algorithm],
                options={"require": ["exp", "sub"]},
            )
        except jwt.InvalidTokenError:
            raise InvalidToken() from None
        return int(claims["sub"])

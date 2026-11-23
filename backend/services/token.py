from datetime import UTC, datetime, timedelta

import jwt

from domain.errors import InvalidToken


class TokenService:
    """Gera e lê os tokens JWT do login."""

    algorithm = "HS256"

    def __init__(self, secret: str, ttl: timedelta):
        self._secret = secret
        self._ttl = ttl

    def issue(self, user_id: int) -> str:
        now = datetime.now(UTC)
        # o JWT exige que o sub seja string
        claims = {"sub": str(user_id), "iat": now, "exp": now + self._ttl}
        return jwt.encode(claims, self._secret, algorithm=self.algorithm)

    def user_id(self, token: str) -> int:
        try:
            # decode confere assinatura e exp; exigir exp barra token que nunca expira
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[self.algorithm],
                options={"require": ["exp", "sub"]},
            )
        except jwt.InvalidTokenError:
            raise InvalidToken() from None
        return int(claims["sub"])

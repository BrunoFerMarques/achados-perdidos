from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()  # argon2


def hash_password(password: str) -> str:
    return _password_hash.hash(password)

import secrets

from pwdlib import PasswordHash

hasher = PasswordHash.recommended()


def verify_password(plain: str, hashed: str) -> bool:
    return hasher.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return hasher.hash(plain)


def create_token() -> str:
    return secrets.token_hex(40)


DUMMY_HASH = hash_password(secrets.token_hex(32))

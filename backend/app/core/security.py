import hashlib
import secrets
from dataclasses import dataclass

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password, password_hash)
    except UnknownHashError:
        return False


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SessionToken:
    raw: str
    hashed: str


def create_session_token() -> SessionToken:
    raw = secrets.token_urlsafe(32)
    return SessionToken(raw=raw, hashed=hash_session_token(raw))

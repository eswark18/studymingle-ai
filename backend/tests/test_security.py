from app.core.security import (
    create_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)


def test_password_is_hashed_and_verified() -> None:
    password = "SafePassword123"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("WrongPassword123", password_hash)


def test_session_token_is_random_and_only_hash_is_stored() -> None:
    first = create_session_token()
    second = create_session_token()

    assert first.raw != second.raw
    assert first.hashed == hash_session_token(first.raw)
    assert first.raw != first.hashed

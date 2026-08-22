"""Security primitives tests: PBKDF2 hashing + JWT."""
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify():
    h = hash_password("s3cret!")
    assert h.startswith("pbkdf2_sha256$")
    assert verify_password("s3cret!", h)
    assert not verify_password("wrong", h)
    assert not verify_password("s3cret!", "garbage")


def test_token_roundtrip():
    token = create_access_token("user-1", "admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["role"] == "admin"


def test_token_rejects_garbage():
    import pytest

    from app.core.security import TokenError

    with pytest.raises(TokenError):
        decode_access_token("not.a.token")

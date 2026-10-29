"""API key generation and Argon2id storage helpers."""

import secrets

from argon2 import PasswordHasher
from argon2.low_level import Type

_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_hasher = PasswordHasher(type=Type.ID)


def _base62_random(entropy_bytes: int = 32) -> str:
    """Encode 256 bits of entropy as an unpadded base62 string."""
    value = int.from_bytes(secrets.token_bytes(entropy_bytes), "big")
    encoded = ""
    while value:
        value, remainder = divmod(value, len(_ALPHABET))
        encoded = _ALPHABET[remainder] + encoded
    return encoded.rjust(43, "0")


def generate_api_key(*, is_test: bool = False) -> str:
    """Return a one-time plaintext key with 32 bytes of random entropy."""
    mode = "test" if is_test else "live"
    return f"rk_{mode}_{_base62_random()}"


def hash_api_key(key: str) -> str:
    """Hash a key with Argon2id for persistent storage."""
    return _hasher.hash(key)


def verify_api_key(key: str, encoded_hash: str) -> bool:
    """Verify a plaintext key against its Argon2id hash."""
    try:
        return _hasher.verify(encoded_hash, key)
    except Exception:
        return False


def display_prefix(key: str) -> str:
    """Return the short, non-secret identifier shown in key listings."""
    return f"{key[:12]}****"

from __future__ import annotations

import hashlib
import hmac
import secrets

KEY_MARKER = "cck"
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_MAXMEM = 64 * 1024 * 1024
_DKLEN = 32


def generate_key() -> tuple[str, str, str]:
    """Return `(plaintext, prefix, secret)` for a brand new API key."""
    prefix = secrets.token_hex(5)
    secret = secrets.token_hex(24)
    return f"{KEY_MARKER}_{prefix}_{secret}", prefix, secret


def split_key(raw_key: str) -> tuple[str, str] | None:
    """Split a presented key into `(prefix, secret)`, or `None` when malformed."""
    parts = raw_key.strip().split("_")
    if len(parts) != 3 or parts[0] != KEY_MARKER:
        return None
    prefix, secret = parts[1], parts[2]
    if not prefix or not secret:
        return None
    return prefix, secret


def hash_secret(secret: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a key secret with scrypt. Returns `(hash_hex, salt)`."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(
        secret.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        maxmem=_SCRYPT_MAXMEM,
        dklen=_DKLEN,
    )
    return digest.hex(), salt


def verify_secret(secret: str, salt: str, expected_hash: str) -> bool:
    """Constant-time comparison between a presented secret and the stored hash."""
    candidate, _ = hash_secret(secret, salt)
    return hmac.compare_digest(candidate, expected_hash)

"""Encryption utilities for sensitive data at rest."""

import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from api.config import settings

logger = logging.getLogger(__name__)

ENCRYPTED_PREFIX = "enc:v1:"
_fernet: Fernet | None = None


def _get_key_path() -> Path:
    return Path(settings.WORKSPACE_DIR) / ".encryption_key"


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet

    # Try env var first
    env_key = os.environ.get("SUNDIAL_ENCRYPTION_KEY")
    if env_key:
        _fernet = Fernet(env_key.encode())
        return _fernet

    # Load or create key file
    key_path = _get_key_path()
    if key_path.exists():
        key = key_path.read_bytes().strip()
    else:
        key = Fernet.generate_key()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(key)
        key_path.chmod(0o600)
        logger.info("Generated encryption key at %s", key_path)

    _fernet = Fernet(key)
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string. Returns prefixed ciphertext."""
    if not plaintext:
        return plaintext
    encrypted = _get_fernet().encrypt(plaintext.encode())
    return ENCRYPTED_PREFIX + encrypted.decode()


def decrypt_value(stored: str) -> str:
    """Decrypt a stored value. Returns plaintext as-is (migration support)."""
    if not stored or not stored.startswith(ENCRYPTED_PREFIX):
        return stored  # Not encrypted, return as-is
    try:
        ciphertext = stored[len(ENCRYPTED_PREFIX) :]
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("Decryption failed - key may have changed")
        return ""  # Return empty on failure

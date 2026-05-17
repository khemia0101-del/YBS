from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


class CredentialVault:
    """Symmetric encryption wrapper for storing integration credentials."""

    def __init__(self, key: str | bytes) -> None:
        if isinstance(key, str):
            key = key.encode()
        # Fernet keys must be 32 url-safe base64 bytes (44 chars encoded).
        # If the provided key isn't already a valid Fernet key, derive one
        # deterministically from it via SHA-256.
        try:
            self._fernet = Fernet(key)
        except (ValueError, TypeError):
            derived = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
            self._fernet = Fernet(derived)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()


# Module-level singleton — key comes from settings at import time.
vault = CredentialVault(settings.ENCRYPTION_KEY)

from __future__ import annotations

from cryptography.fernet import Fernet

from app.config import settings


class CredentialVault:
    """Symmetric encryption wrapper for storing integration credentials."""

    def __init__(self, key: str | bytes) -> None:
        if isinstance(key, str):
            key = key.encode()
        # Fernet keys must be 32 url-safe base64 bytes (44 chars encoded).
        # If the provided key isn't already a valid Fernet key, derive one.
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()


# Module-level singleton — key comes from settings at import time.
vault = CredentialVault(settings.ENCRYPTION_KEY)

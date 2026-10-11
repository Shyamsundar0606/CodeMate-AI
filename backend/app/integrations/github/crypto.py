import json
import uuid

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings
from app.integrations.github.exceptions import GitHubError


class CredentialCipher:
    """Authenticated ciphertext bound to its owner and purpose, preventing row swaps."""

    def __init__(self, settings: Settings):
        key = settings.github_token_encryption_key
        if key is None:
            raise GitHubError("GITHUB_NOT_CONFIGURED", "GitHub integration is not configured.", 503)
        self.fernet = Fernet(key.get_secret_value().encode())

    def encrypt(self, owner: uuid.UUID, purpose: str, value: str) -> str:
        data = json.dumps({"owner": str(owner), "purpose": purpose, "value": value}).encode()
        return self.fernet.encrypt(data).decode()

    def decrypt(self, owner: uuid.UUID, purpose: str, ciphertext: str) -> str:
        try:
            data = json.loads(self.fernet.decrypt(ciphertext.encode()))
            if (
                data["owner"] != str(owner)
                or data["purpose"] != purpose
                or not isinstance(data["value"], str)
            ):
                raise ValueError("Credential ownership mismatch")
            return data["value"]
        except (InvalidToken, ValueError, TypeError, KeyError) as exc:
            raise GitHubError(
                "GITHUB_CREDENTIAL_UNAVAILABLE",
                "Stored GitHub credentials cannot be used. Disconnect and reconnect.",
                503,
            ) from exc

import logging
import os
from typing import Optional

from azure.identity import DefaultAzureCredential, CredentialUnavailableError
from azure.keyvault.secrets import SecretClient

from config import Settings


class SecretProvider:
    """Resolves secrets from Azure Key Vault with environment fallbacks."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: Optional[SecretClient] = None
        self._logger = logging.getLogger(__name__)

        if settings.key_vault_uri:
            try:
                credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
                self._client = SecretClient(vault_url=settings.key_vault_uri, credential=credential)
            except CredentialUnavailableError as exc:
                self._logger.warning("DefaultAzureCredential unavailable: %s", exc)
            except Exception as exc:  # pylint: disable=broad-except
                self._logger.warning("Failed to initialize SecretClient: %s", exc)

    def get_secret(self, secret_name: str, *, fallback_env: str | None = None, default: str | None = None) -> str | None:
        if not secret_name:
            return default

        if self._client:
            try:
                secret = self._client.get_secret(secret_name)
                if secret and secret.value:
                    return secret.value
            except Exception as exc:  # pylint: disable=broad-except
                self._logger.warning("Secret %s not available in Key Vault: %s", secret_name, exc)

        env_name = fallback_env or secret_name.upper()
        return os.getenv(env_name, default)

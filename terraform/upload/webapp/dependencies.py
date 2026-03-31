from functools import lru_cache

from config import settings
from services.llm_client import AzureFoundryClient
from services.registry import AzureTableStorageRepository
from services.secret_provider import SecretProvider


@lru_cache
def get_secret_provider() -> SecretProvider:
    return SecretProvider(settings)


@lru_cache
def get_registry_repository() -> AzureTableStorageRepository:
    """
    Returns the appropriate registry repository based on DATA_PROVIDER configuration.
    
    Set DATA_PROVIDER environment variable to:
    Use Azure Table Storage AzureTableStorageRepository
    """
    secrets = get_secret_provider()
    return AzureTableStorageRepository(settings, secrets)


@lru_cache
def get_llm_client() -> AzureFoundryClient:
    return AzureFoundryClient(settings, get_secret_provider())

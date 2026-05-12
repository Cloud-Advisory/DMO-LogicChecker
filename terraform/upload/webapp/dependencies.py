"""Dependency providers for the web application.

This module defines factory functions for shared service dependencies. Each
provider is wrapped with lru_cache so that the same instance is reused during
application runtime.
"""

from functools import lru_cache

from config import settings
from services.llm_client import AzureFoundryClient
from services.registry import AzureStorageTableLLMInteractionRegistry, AzureTableStorageRepository
from services.secret_provider import SecretProvider


@lru_cache
def get_secret_provider() -> SecretProvider:
    """Create and cache the application secret provider.

    The SecretProvider is responsible for resolving secrets from configured
    vaults or secret storage and is shared across other dependency providers.
    """
    return SecretProvider(settings)


@lru_cache
def get_registry_repository() -> AzureTableStorageRepository:
    """Create and cache the registry repository instance.

    This repository is used to persist and retrieve registry metadata using
    Azure Table Storage.
    """
    secrets = get_secret_provider()
    return AzureTableStorageRepository(settings, secrets)


@lru_cache
def get_llm_interaction_registry() -> AzureStorageTableLLMInteractionRegistry:
    """Create and cache the LLM interaction registry.

    The interaction registry stores prompts, responses, and metadata for LLM
    interactions in Azure Table Storage.
    """
    secrets = get_secret_provider()
    return AzureStorageTableLLMInteractionRegistry(settings, secrets)


@lru_cache
def get_llm_client() -> AzureFoundryClient:
    """Create and cache the Azure Foundry LLM client.

    The LLM client is used to send requests to the configured Azure Foundry
    language model service.
    """
    return AzureFoundryClient(settings, get_secret_provider())

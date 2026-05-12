"""Configuration module for the webapp.

This module loads settings from environment variables, local.settings.json files
for local development, and .env files. It also provides a Settings model with
parsing helpers for complex values such as JSON-encoded lists and dictionaries.
"""

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict



def _load_local_settings() -> None:
    """Load local settings from a JSON file into the process environment.

    This is intended to mirror Azure Static Web Apps / Functions behavior by
    reading `local.settings.json` and populating `os.environ` with the values
    found under the top-level `Values` dictionary.
    """

    candidate_paths: List[Path] = []
    env_override = os.getenv("LOCAL_SETTINGS_FILE")
    if env_override:
        candidate_paths.append(Path(env_override))

    repo_root = Path(__file__).resolve().parents[1]
    candidate_paths.append(repo_root / "local.settings.json")

    for path in candidate_paths:
        if not path.is_file():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:  # pylint: disable=broad-except
            logging.getLogger(__name__).warning("Failed to parse %s: %s", path, exc)
            continue

        values = payload.get("Values") if isinstance(payload, dict) else None
        if not isinstance(values, dict):
            continue

        # Only set values that are not already present in the environment.
        for key, value in values.items():
            if key and key not in os.environ:
                os.environ[key] = str(value)
        break


_load_local_settings()


class LenientEnvSource(EnvSettingsSource):
    """Environment source that tolerates invalid JSON for complex fields."""

    def decode_complex_value(self, field_name, field, value):
        """Decode JSON values when possible, otherwise return raw string.

        Pydantic's default behavior raises on invalid JSON for fields like lists
        or dictionaries. This class allows plain strings to pass through for
        later custom parsing.
        """
        try:
            return super().decode_complex_value(field_name, field, value)
        except json.JSONDecodeError:
            return value


class Settings(BaseSettings):
    """Central configuration object for the webapp.

    Settings are loaded from environment variables first, then .env files,
    and finally from secrets if available.
    """

    app_name: str = Field(default="SITS Logic Checker", alias="APP_NAME")
    app_region: str = Field(default="westeurope", alias="APP_REGION")
    identity_mode: str = Field(default="token", alias="IDENTITY_MODE")
    allowed_origins: List[str] = Field(default_factory=list, alias="ALLOWED_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")

    openai_api_base: str = Field(default="", alias="OPENAI_API_BASE")
    openai_deployment_name: str = Field(default="gpt-5-mini", alias="OPENAI_DEPLOYMENT_NAME")
    openai_api_version: str = Field(default="2025-04-01-preview", alias="OPENAI_API_VERSION")
    openai_key_secret_name: str = Field(default="openai-api-key", alias="OPENAI_KEY_SECRET_NAME")
    prompt_secret_name: str = Field(default="prompt-template", alias="PROMPT_SECRET_NAME")
    openai_model_profile: dict[str, Any] | None = Field(default=None, alias="OPENAI_MODEL_PROFILE")
    openai_temperature: float | None = Field(default=None, alias="OPENAI_TEMPERATURE")
    openai_top_p: float | None = Field(default=None, alias="OPENAI_TOP_P")

    storage_account_name: str = Field(default="", alias="STORAGE_ACCOUNT_NAME")
    storage_table_name: str = Field(default="ApiConfig", alias="STORAGE_TABLE_NAME")
    llm_interaction_table_name: str = Field(default="InteractionLogs", alias="LLM_INTERACTION_TABLE_NAME")

    data_provider: str = Field(default="table", alias="DATA_PROVIDER")

    key_vault_uri: str | None = Field(default=None, alias="KEY_VAULT_URI")
    static_base_url: str | None = Field(default=None, alias="STATIC_BASE_URL")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    timeout_seconds: int = Field(default=60, alias="LLM_TIMEOUT_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Customize the order of settings sources used by Pydantic."""
        return (
            init_settings,
            LenientEnvSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: List[str] | str | None) -> List[str]:
        """Parse allowed origins from a list, JSON string, or comma-separated string."""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            clean = value.strip()
            if not clean:
                return []
            try:
                parsed = json.loads(clean)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            except json.JSONDecodeError:
                pass
            return [origin.strip() for origin in clean.split(",") if origin.strip()]
        return []

    @field_validator("openai_model_profile", mode="before")
    @classmethod
    def parse_model_profile(cls, value: dict[str, Any] | str | None) -> dict[str, Any] | None:
        """Parse OpenAI model profile from JSON string or dictionary value."""
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            clean = value.strip()
            if not clean:
                return None
            try:
                parsed = json.loads(clean)
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                logging.getLogger(__name__).warning("OPENAI_MODEL_PROFILE is not valid JSON; ignoring.")
                return None
        return None


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance for the current process."""
    return Settings()


settings = get_settings()

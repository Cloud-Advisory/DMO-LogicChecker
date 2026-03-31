import logging
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from openai import AzureOpenAI, BadRequestError

from config import Settings
from services.secret_provider import SecretProvider

@dataclass
class EndpointDetails:
    base_endpoint: str
    deployment: str | None
    api_version: str | None


@dataclass
class ModelProfile:
    deployment: str | None = None
    api_version: str | None = None
    supports_temperature: bool = True
    supports_top_p: bool = True
    default_temperature: float | None = None
    default_top_p: float | None = None
    max_completion_tokens: int | None = None

    @classmethod
    def from_settings(cls, payload: dict[str, Any] | None) -> "ModelProfile":
        if not payload:
            return cls()

        supports = payload.get("supports") if isinstance(payload.get("supports"), dict) else {}

        return cls(
            deployment=payload.get("deployment"),
            api_version=payload.get("apiVersion") or payload.get("api_version"),
            supports_temperature=bool(payload.get("supportsTemperature", supports.get("temperature", True))),
            supports_top_p=bool(payload.get("supportsTopP", supports.get("topP", True))),
            default_temperature=payload.get("temperature"),
            default_top_p=payload.get("topP"),
            max_completion_tokens=payload.get("maxCompletionTokens") or payload.get("max_completion_tokens"),
        )


class AzureFoundryClient:
    """Thin wrapper around Azure AI Foundry (Azure OpenAI) chat completions."""

    def __init__(self, settings: Settings, secrets: SecretProvider):
        self._settings = settings
        self._secrets = secrets
        self._logger = logging.getLogger(__name__)
        self._client: Optional[AzureOpenAI] = None
        self._client_deployment: str | None = None
        profile_payload = settings.openai_model_profile #or DEFAULT_MODEL_PROFILE
        self._profile = ModelProfile.from_settings(profile_payload)

    def _extract_endpoint_details(self, raw_endpoint: str) -> EndpointDetails:
        cleaned = (raw_endpoint or "").strip()
        if not cleaned:
            raise RuntimeError("Azure AI Foundry endpoint is not configured.")

        parsed = urlparse(cleaned)
        if parsed.scheme and parsed.netloc:
            base = f"{parsed.scheme}://{parsed.netloc}"
        else:
            base = cleaned.rstrip("/")

        deployment: str | None = None
        api_version: str | None = None

        path_segments = [segment for segment in parsed.path.split("/") if segment]
        if len(path_segments) >= 3 and path_segments[0].lower() == "openai" and path_segments[1].lower() == "deployments":
            deployment = path_segments[2]

        query = parse_qs(parsed.query)
        api_version = query.get("api-version", [None])[0]

        if not parsed.scheme:
            # Handle cases where the endpoint was already the base URL without scheme in urlparse result
            base = cleaned.rstrip("/")

        return EndpointDetails(base_endpoint=base.rstrip("/"), deployment=deployment, api_version=api_version)

    def _build_client(self, *, endpoint: str | None = None, api_key: str | None = None) -> tuple[AzureOpenAI, str]:
        details = self._extract_endpoint_details(endpoint or self._settings.openai_api_base)

        resolved_key = api_key or self._secrets.get_secret(
            self._settings.openai_key_secret_name,
            fallback_env="AZURE_OPENAI_KEY",
        )
        if not resolved_key:
            raise RuntimeError("Azure AI Foundry API key is missing.")

        api_version = details.api_version or self._profile.api_version or self._settings.openai_api_version
        if not api_version:
            raise RuntimeError("Azure AI Foundry API version is not configured.")

        deployment_name = details.deployment or self._profile.deployment or self._settings.openai_deployment_name
        if not deployment_name:
            raise RuntimeError(
                "Azure AI Foundry deployment name is not configured. Set OPENAI_DEPLOYMENT_NAME or include /deployments/<name>/ in OPENAI_API_BASE."
            )

        client = AzureOpenAI(
            api_key=resolved_key,
            api_version=api_version,
            azure_endpoint=details.base_endpoint,
        )

        return client, deployment_name

    def _get_client(self) -> tuple[AzureOpenAI, str]:
        if not self._client or not self._client_deployment:
            self._client, self._client_deployment = self._build_client()
        return self._client, self._client_deployment

    def run_completion(
        self,
        *,
        prompt: str,
        user_text: str,
        max_tokens: int = 3500,
        endpoint_override: str | None = None,
        api_key_override: str | None = None,
    ) -> str:
        if endpoint_override or api_key_override:
            client, deployment_name = self._build_client(endpoint=endpoint_override, api_key=api_key_override)
        else:
            client, deployment_name = self._get_client()

        resolved_max_tokens = max_tokens or self._profile.max_completion_tokens or 3500

        request_kwargs: dict[str, Any] = {
            "model": deployment_name,
            "max_completion_tokens": resolved_max_tokens,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text},
            ],
        }

        temperature_value = self._settings.openai_temperature
        if temperature_value is None:
            temperature_value = self._profile.default_temperature

        if temperature_value is not None and self._profile.supports_temperature:
            request_kwargs["temperature"] = temperature_value

        top_p_value = self._settings.openai_top_p
        if top_p_value is None:
            top_p_value = self._profile.default_top_p

        if top_p_value is not None and self._profile.supports_top_p:
            request_kwargs["top_p"] = top_p_value

        response = self._invoke_with_parameter_fallback(client, dict(request_kwargs))

        try:
            return response.choices[0].message.content  # type: ignore[index]
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.error("Azure AI Foundry response parsing failed: %s", exc)
            raise

    def _invoke_with_parameter_fallback(self, client: AzureOpenAI, payload: dict[str, Any]):
        disabled_fields: set[str] = set()

        while True:
            try:
                return client.chat.completions.create(**payload)
            except BadRequestError as exc:
                if self._try_disable_unsupported_field(payload, exc, disabled_fields):
                    continue
                raise

    def _try_disable_unsupported_field(self, payload: dict[str, Any], exc: BadRequestError, disabled_fields: set[str]) -> bool:
        error_text = self._extract_error_text(exc)

        for field in ("temperature", "top_p"):
            if field in payload and field not in disabled_fields and field in error_text and "unsupported" in error_text:
                disabled_fields.add(field)
                payload.pop(field, None)
                self._logger.warning("Model rejected %s parameter; retrying without it.", field)
                return True

        return False

    @staticmethod
    def _extract_error_text(exc: BadRequestError) -> str:
        parts: list[str] = []
        for attr in ("message", "body", "response"):
            value = getattr(exc, attr, None)
            if not value:
                continue
            parts.append(str(value))

        if not parts and exc.args:
            parts.extend(str(arg) for arg in exc.args)

        return " ".join(parts).lower()

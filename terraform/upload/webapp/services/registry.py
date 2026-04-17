import logging
from typing import Any, List, Optional
from azure.identity import DefaultAzureCredential

from azure.data.tables import TableClient, TableServiceClient
from azure.core.exceptions import ResourceNotFoundError

from config import Settings
from services.secret_provider import SecretProvider


class AzureTableStorageRepository:
    """Reads token/action metadata from Azure Table Storage."""

    def __init__(self, settings: Settings, secrets: SecretProvider):
        self._settings = settings
        self._secrets = secrets
        self._logger = logging.getLogger(__name__)
        self._table_client: Optional[TableClient] = None
        self._initialize_table_client()

    def _initialize_table_client(self):
        """Initialize the Azure Table Storage client."""
        storage_account_name = self._settings.storage_account_name.strip()
        table_name = self._settings.storage_table_name.strip()

        if not storage_account_name:
            raise RuntimeError("STORAGE_ACCOUNT_NAME is not configured.")
        if not table_name:
            raise RuntimeError("STORAGE_TABLE_NAME is not configured.")

        try:
            credential = DefaultAzureCredential()
            table_service_client = TableServiceClient(
                endpoint=f"https://{storage_account_name}.table.core.windows.net/",
                credential=credential,
            )
            self._table_client = table_service_client.get_table_client(table_name)

            self._logger.info(
                "Successfully initialized Azure Table Storage client for table %s in account %s",
                table_name,
                storage_account_name,
            )
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.error("Failed to initialize Azure Table Storage client: %s", exc)
            raise

    @staticmethod
    def _normalize_entity(entity: dict[str, Any]) -> dict[str, Any]:
        """Normalize an Azure Table Storage entity to match SQL schema."""
        return {
            "token": entity.get("PartitionKey"),
            "action": entity.get("RowKey"),
            "api_key": entity.get("api_key"),
            "endpoint": entity.get("endpoint"),
            "prompt": entity.get("prompt", ""),
        }

    def fetch_route(self, token: str, action: str) -> Optional[dict[str, Any]]:
        """Fetch a single route by token and action."""
        if not self._table_client:
            self._logger.error("Table client not initialized")
            return None

        try:
            entity = self._table_client.get_entity(partition_key=token, row_key=action)
            return self._normalize_entity(entity)
        except ResourceNotFoundError:
            return None
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.error("Failed to fetch route %s/%s: %s", token, action, exc)
            return None

    def list_routes(self, limit: int = 200) -> List[dict[str, Any]]:
        """List all routes with an optional limit."""
        if not self._table_client:
            self._logger.error("Table client not initialized")
            return []

        limit = min(max(limit, 1), 1000)

        try:
            entities = self._table_client.query_entities("")
            routes = []
            for entity in entities:
                routes.append(self._normalize_entity(entity))
                if len(routes) >= limit:
                    break
            return routes
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.error("Failed to list routes: %s", exc)
            return []

    def upsert_route(
        self,
        *,
        token: str,
        action: str,
        prompt: str | None,
        endpoint: str | None,
        api_key: str | None,
    ) -> dict[str, Any]:
        """Insert or update a route."""
        if not self._table_client:
            self._logger.error("Table client not initialized")
            raise RuntimeError("Table client not initialized")

        entity = {
            "PartitionKey": token,
            "RowKey": action,
            "api_key": api_key,
            "endpoint": endpoint,
            "prompt": prompt,
        }

        try:
            self._table_client.upsert_entity(entity)
            return {
                "token": token,
                "action": action,
                "api_key": api_key,
                "endpoint": endpoint,
                "prompt": prompt,
            }
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.error("Failed to upsert route %s/%s: %s", token, action, exc)
            raise

    def delete_route(self, token: str, action: str) -> bool:
        """Delete a route by token and action."""
        if not self._table_client:
            self._logger.error("Table client not initialized")
            raise RuntimeError("Table client not initialized")

        try:
            self._table_client.delete_entity(partition_key=token, row_key=action)
            return True
        except ResourceNotFoundError:
            return False
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.error("Failed to delete route %s/%s: %s", token, action, exc)
            raise


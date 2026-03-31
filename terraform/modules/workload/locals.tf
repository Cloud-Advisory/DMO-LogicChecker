locals {
  # Naming convention
  storage_account_name      = substr("st${var.name_prefix}${random_string.unique.result}", 0, 24)
  key_vault_name            = substr("${var.name_prefix}kv${random_string.unique.result}", 0, 24)
  app_service_plan_name     = "${var.name_prefix}-asp-${random_string.unique.result}"
  web_app_name              = "${var.name_prefix}-api-${random_string.unique.result}"
  openai_account_name       = "${var.name_prefix}-aoai-${random_string.unique.result}"
  application_insights_name = "${var.name_prefix}-appi-${random_string.unique.result}"

  # Logic from Bicep
  identity_mode = var.enable_entra_id ? "entra" : "token"
  allowed_origins = [
    # "https://logicchecker-api-ciogefddvd3ai.azurewebsites.net",
    trimsuffix(azurerm_storage_account.main.primary_web_endpoint, "/")
  ]
}


# --------------------------------------------------------------------------------------------------
# Terraform module for deploying the workload components: Storage Account, Key Vault, Azure OpenAI, and Web App
# Random string resource is used to generate unique suffixes for resource names to avoid naming conflicts. (locals.tf)
# --------------------------------------------------------------------------------------------------

resource "random_string" "unique" {
  length  = 8
  special = false
  upper   = false
}

# --------------------------------------------------------------------------------------------------
# Storage Account and Table
# --------------------------------------------------------------------------------------------------


resource "azurerm_storage_account" "main" {
  name                          = local.storage_account_name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  min_tls_version               = "TLS1_2"
  public_network_access_enabled = var.enable_private_networking ? false : true
  tags                          = var.resource_tags
}

resource "azurerm_storage_table" "main" {
  name                 = "ApiConfig"
  storage_account_name = azurerm_storage_account.main.name
}

resource "azurerm_private_endpoint" "storage_account" {
  count               = var.enable_private_networking ? 1 : 0
  name                = "pep-${azurerm_storage_account.main.name}"
  location            = azurerm_storage_account.main.location
  resource_group_name = azurerm_storage_account.main.resource_group_name
  subnet_id           = var.subnet_id

  private_service_connection {
    name                           = "privateserviceconnection"
    private_connection_resource_id = azurerm_storage_account.main.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }
}


# --------------------------------------------------------------------------------------------------
# Key Vault and Secrets
# --------------------------------------------------------------------------------------------------

resource "azurerm_key_vault" "main" {
  name                          = local.key_vault_name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  tenant_id                     = var.aad_tenant_id
  sku_name                      = "standard"
  soft_delete_retention_days    = 7
  purge_protection_enabled      = true
  public_network_access_enabled = true
  tags                          = var.resource_tags
  rbac_authorization_enabled    = true
}
resource "azurerm_key_vault_secret" "storage_key" {
  name         = "storage-account-key"
  value        = azurerm_storage_account.main.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on = [
    azurerm_storage_account.main,
    azurerm_role_assignment.kv_secrets_officer,
    azurerm_key_vault.main,
  ]
}
resource "azurerm_key_vault_secret" "openai_key" {
  count        = var.deploy_azure_openai ? 1 : 0
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.main[0].primary_access_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on = [
    azurerm_cognitive_account.main,
    azurerm_role_assignment.kv_secrets_officer,
    azurerm_key_vault.main,
  ]
}
resource "azurerm_key_vault_secret" "entra_id_auth_secret" {
  name         = "entra-id-auth-secret"
  value        = azuread_application_password.this.value
  key_vault_id = azurerm_key_vault.main.id
  depends_on = [
    azuread_application_password.this,
    azurerm_role_assignment.kv_secrets_officer,
    azurerm_key_vault.main,
  ]
}
resource "azurerm_key_vault_secret" "prompt_template" {
  name         = "prompt-template"
  value        = var.prompt_template
  key_vault_id = azurerm_key_vault.main.id
  depends_on = [
    azuread_application_password.this,
    azurerm_role_assignment.kv_secrets_officer,
    azurerm_key_vault.main,
  ]
}

# Private Endpoint
resource "azurerm_private_endpoint" "key_vault" {
  count               = var.enable_private_networking ? 1 : 0
  name                = "pep-${azurerm_key_vault.main.name}"
  location            = azurerm_key_vault.main.location
  resource_group_name = azurerm_key_vault.main.resource_group_name
  subnet_id           = var.subnet_id

  private_service_connection {
    name                           = "privateserviceconnection"
    private_connection_resource_id = azurerm_key_vault.main.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }
}


# --------------------------------------------------------------------------------------------------
# Azure OpenAI
# --------------------------------------------------------------------------------------------------

resource "azurerm_application_insights" "main" {
  count               = var.enable_entra_id ? 1 : 0
  name                = local.application_insights_name
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = "web"
  tags                = var.resource_tags
}

resource "azurerm_cognitive_account" "main" {
  count                         = var.deploy_azure_openai ? 1 : 0
  name                          = local.openai_account_name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  kind                          = "OpenAI"
  custom_subdomain_name         = local.openai_account_name
  sku_name                      = "S0"
  public_network_access_enabled = true
  tags                          = var.resource_tags
}

# gpt-5-mini deployment
resource "azurerm_cognitive_deployment" "gpt-5-mini" {
  name                 = var.openai_deployment_name
  cognitive_account_id = azurerm_cognitive_account.main[0].id
  rai_policy_name      = "Microsoft.DefaultV2"
  model {
    format  = "OpenAI"
    name    = var.openai_deployment_name
    version = var.openai_module_version
  }
  sku {
    name = "GlobalStandard"
  }
}


# -------------------------------------------------------------------------------------------------
# Web App
# --------------------------------------------------------------------------------------------------

resource "azurerm_service_plan" "main" {
  name                = local.app_service_plan_name
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku
  tags                = var.resource_tags
}

resource "azurerm_linux_web_app" "main" {
  name                = local.web_app_name
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.main.id
  https_only          = true
  tags                = var.resource_tags

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.14"
    }
    always_on           = true
    ftps_state          = "Disabled"
    minimum_tls_version = "1.2"
  }

  app_settings = {

    PYTHON_VERSION  = "3.14"
    APP_REGION      = var.location
    IDENTITY_MODE   = local.identity_mode
    KEY_VAULT_URI   = azurerm_key_vault.main.vault_uri
    ALLOWED_ORIGINS = join(",", local.allowed_origins)
    DATA_PROVIDER   = "table"

    # Conditional settings
    APPINSIGHTS_INSTRUMENTATIONKEY        = var.enable_entra_id ? azurerm_application_insights.main[0].instrumentation_key : null
    APPLICATIONINSIGHTS_CONNECTION_STRING = var.enable_entra_id ? azurerm_application_insights.main[0].connection_string : null

    OPENAI_API_BASE        = var.deploy_azure_openai ? azurerm_cognitive_account.main[0].endpoint : null
    OPENAI_KEY_SECRET_NAME = "openai-api-key"
    OPENAI_API_VERSION     = var.openai_api_version
    OPENAI_DEPLOYMENT_NAME = var.openai_deployment_name # var.deploy_azure_openai ? "gpt-5-mini" : null

    STORAGE_ACCOUNT_NAME            = azurerm_storage_account.main.name
    STORAGE_ACCOUNT_KEY_SECRET_NAME = "storage-account-key"
    STORAGE_TABLE_NAME              = "ApiConfig"

    SCM_DO_BUILD_DURING_DEPLOYMENT           = "1"
    MICROSOFT_PROVIDER_AUTHENTICATION_SECRET = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.main.name};SecretName=${azurerm_key_vault_secret.entra_id_auth_secret.name})" #azuread_application_password.this.value
  }

  auth_settings_v2 {
    login {
      token_store_enabled = true
    }
    require_authentication = true
    auth_enabled           = var.enable_entra_id
    unauthenticated_action = var.enable_entra_id ? "RedirectToLoginPage" : "AllowAnonymous"
    default_provider       = var.enable_entra_id ? "azureactivedirectory" : null
    active_directory_v2 {
      client_id                  = azuread_application.this.client_id
      tenant_auth_endpoint       = "https://login.microsoftonline.com/${var.aad_tenant_id}/v2.0"
      client_secret_setting_name = "MICROSOFT_PROVIDER_AUTHENTICATION_SECRET"
    }
  }

  depends_on = [
    azurerm_key_vault.main,
    azurerm_storage_account.main,
    azuread_application.this
  ]
  lifecycle {
    ignore_changes = [tags]
  }
}

# Private Endpoint
resource "azurerm_private_endpoint" "linux_web_app" {
  count               = var.enable_private_networking ? 1 : 0
  name                = "pep-${azurerm_linux_web_app.main.name}"
  location            = azurerm_linux_web_app.main.location
  resource_group_name = azurerm_linux_web_app.main.resource_group_name
  subnet_id           = var.subnet_id

  private_service_connection {
    name                           = "privateserviceconnection"
    private_connection_resource_id = azurerm_linux_web_app.main.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }
}

# --------------------------------------------------------------------------------------------------
# Role Assignments
# --------------------------------------------------------------------------------------------------

# RBAC Permission for Deploying Principal to manage Key Vault secrets (needed for initial deployment and future updates)
resource "azurerm_role_assignment" "kv_secrets_officer" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = var.deploying_principal_object_id
}

# Add RBAC for the web app's managed identity
resource "azurerm_role_assignment" "kv_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.main.identity[0].principal_id
}
resource "azurerm_role_assignment" "blob_data_reader" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_linux_web_app.main.identity[0].principal_id
}
resource "azurerm_role_assignment" "table_data_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_linux_web_app.main.identity[0].principal_id
}

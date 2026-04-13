provider "azurerm" {
  features {
    resource_group { # Needed because of Smart detector alert rule when destroying resource group
      prevent_deletion_if_contains_resources = false
    }
  }
  subscription_id = "<<subscription_id>>"
}

provider "azuread" {
  tenant_id = "<<tenant_id>>"
}

provider "archive" {}


# All necessary resource providers must be registered so that the Azure resources can be created. If they already exist in the subscription, they need to imported into the state. The import blocks below can be used for that. After a successful import, they can be removed from the code.

# List of Azure resource providers required for this deployment; used to ensure all necessary providers are registered.
locals {
  resource_providers = {
    "Microsoft.Web"               = true,
    "Microsoft.Storage"           = true,
    "Microsoft.KeyVault"          = true,
    "Microsoft.CognitiveServices" = true,
    "Microsoft.DocumentDB"        = true,
    "Microsoft.ContainerRegistry" = true,
  }
}

resource "azurerm_resource_provider_registration" "all" {
  for_each = { for k, v in local.resource_providers : k => v if v }
  name     = each.key
}

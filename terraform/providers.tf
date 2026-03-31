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

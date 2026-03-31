# DMO LogicChecker - Quick Deployment Guide

## Prerequisites

- **Azure Subscription** with Owner permissions
- **Local tools**:
  - Azure CLI ([install](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli))
  - Terraform `>=1.14` ([install](https://developer.hashicorp.com/terraform/install)) or Tofu `>=1.11` [install](https://opentofu.org/docs/intro/install/)
  - PowerShell `>=5.1`

---

## Quick Start (5 Steps)

### 1. Clone & Navigate
```powershell
git clone <repo>
cd <repo>/terraform
```

### 2. Login to Azure
```powershell
az login
```

### 3. Prepare Configuration

**Edit `providers.tf`** - Set your Azure details:
```hcl
provider "azurerm" {
  subscription_id = "YOUR-SUBSCRIPTION-ID"  # Add your subscription ID
}
provider "azuread" {
  tenant_id = "YOUR-TENANT-ID"  # Add your tenant ID
}
```

**Create `terraform.tfvars`** - Copy from example and update:
```hcl
subscription_id           = "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
resource_group_name       = "rg-dmo-logicchecker-01"
location                  = "germanywestcentral"
name_prefix               = "logicchecker"
sku                       = "B1"  # Use B1 for testing, P0v3 for production
enable_entra_id           = true
deploy_azure_openai       = true
openai_api_version        = "2025-04-01-preview"
openai_module_version     = "2025-08-07"
openai_deployment_name    = "gpt-5-mini"
enable_private_networking = false

resource_tags = {
  environment     = "development"
  workload        = "logicchecker"
  owner           = "Firstname Lastname"
}
```

### 4. Deploy
```powershell
terraform init
terraform plan -out plan.tfplan
terraform apply -auto-approve plan.tfplan
```

### 5. Get Your App URL
```powershell
terraform output
```

Look for `web_app_name` - your app runs at: `https://{web_app_name}.azurewebsites.net`

---

## What Gets Created

- **Resource Group** - Contains all resources
- **Web App** - Python FastAPI backend (Linux App Service)
- **Azure OpenAI** - Optional LLM service (gpt-5-mini)
- **Storage Account** - For config storage
- **Key Vault** - For secrets management
- **Entra ID** - Authentication setup (optional)

---

## Cleanup

Remove all resources:
```powershell
terraform destroy
```

---

## Common Issues

| Issue | Solution |
|-------|----------|
| `subscription_id not found` | Set correct subscription ID in `providers.tf` |
| `Insufficient permissions` | Ensure you have Owner role in Azure subscription |
| `Resource already exists` | Change `name_prefix` in `terraform.tfvars` |

For more details: See `terraform output` after deployment.

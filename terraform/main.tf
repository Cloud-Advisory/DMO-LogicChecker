
# --------------------------------------------------------------------------------------------------
# This Terraform configuration defines the infrastructure for the Logic Checker application, including a resource group, storage account, key vault, Azure OpenAI deployment, and a web app. It also includes a null_resource to handle the deployment of the backend code to the web app after the infrastructure is provisioned.
# --------------------------------------------------------------------------------------------------


resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.resource_tags
}

module "workload" {
  source = "./modules/workload"

  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  name_prefix                   = var.name_prefix
  resource_tags                 = var.resource_tags
  enable_entra_id               = var.enable_entra_id
  aad_tenant_id                 = data.azurerm_client_config.current.tenant_id
  deploying_principal_object_id = data.azurerm_client_config.current.object_id
  deploy_azure_openai           = var.deploy_azure_openai
  sku                           = var.sku
  openai_api_version            = var.openai_api_version
  openai_module_version         = var.openai_module_version
  openai_deployment_name        = var.openai_deployment_name
  openai_deployment_capacity    = var.openai_deployment_capacity
  devtest_deployment            = var.devtest_deployment
  enable_private_networking     = var.enable_private_networking
  prompt_template               = var.prompt_template
}


# --------------------------------------------------------------------------------------------------
# The null_resource "app_deployer" is used to deploy the backend code to the Azure Web App after the infrastructure is provisioned. It uses the Azure CLI to perform the deployment and is triggered to run whenever the web app or storage account is recreated, or when the source code changes (as determined by the hash of the zip file).
# --------------------------------------------------------------------------------------------------

resource "null_resource" "app_deployer" {
  # Rerun these steps if the web app or storage account is recreated
  triggers = {
    web_app_id         = module.workload.web_app_name
    storage_account_id = module.workload.storage_account_name
    archive_file       = module.workload.archive_file
    source_hash        = filesha256(module.workload.zip_output_path) # "upload/webapp.zip" This ensures the provisioner runs again if the backend code changes and is re-zipped
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Deploying backend to Web App..."
      az account set --subscription ${var.subscription_id}
      az webapp deploy --resource-group "${var.resource_group_name}" --name "${module.workload.web_app_name}" --src-path ${module.workload.zip_output_path} --type zip

    EOT
    # This assumes the 'az' CLI is logged in and 'zip' is available.
    # The working directory for this command is `terraform/`
    working_dir = abspath(path.module)
    interpreter = ["Powershell", "-c"]
  }
  depends_on = [
    module.workload

  ]
}

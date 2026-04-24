variable "resource_group_name" {
  description = "Name of the resource group that will be created or updated for this workload."
  type        = string
}
variable "location" {
  description = "Azure region for every resource."
  type        = string
  default     = "germanywestcentral"
}
variable "name_prefix" {
  description = "Short prefix applied to resource names to keep them unique."
  type        = string
  default     = "logicchecker"
}
variable "enable_entra_id" {
  description = "Enable Microsoft Entra ID authentication for the backend App Service."
  type        = bool
  default     = true
}
variable "deploy_azure_openai" {
  description = "Deploy Azure OpenAI (Azure AI Foundry) account into the resource group."
  type        = bool
  default     = true
}
variable "sku" {
  description = "SKU for the App Service Plan."
  type        = string
  default     = "B1"
}
variable "resource_tags" {
  description = "Custom tags applied to each resource."
  type        = map(string)
}
variable "openai_api_version" {
  description = "API version for Azure OpenAI."
  type        = string
  default     = "2025-04-01-preview"
}
variable "openai_module_version" {
  description = "Module version for Azure OpenAI."
  type        = string
  default     = "2025-08-07"
}
variable "openai_deployment_name" {
  description = "Model name for Azure OpenAI."
  type        = string
  default     = "gpt-5-mini"
}
variable "openai_deployment_capacity" {
  description = "Capacity for Azure OpenAI deployment (number of instances)."
  type        = number
  default     = 1
}
variable "subscription_id" {
  description = "Azure Subscription ID where the resources will be deployed."
  type        = string
}
variable "devtest_deployment" {
  description = "Flag to indicate if the deployment is for development/testing or production."
  type        = bool
  default     = true
}
variable "enable_private_networking" {
  description = "If value is true, public networking will be disabled and private endpoints will be created for Azure Storage and Azure OpenAI."
  type        = bool
}

variable "prompt_template" {
  description = "Default AI prompt template saved to Key Vault secret 'prompt-template'."
  type        = string
  default     = "You are a medical documentation assistant supporting clinicians. Return well-structured German text, preserve clinical accuracy, and never invent data."
}

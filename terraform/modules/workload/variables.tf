variable "resource_group_name" {
  description = "The name of the resource group."
  type        = string
}
variable "location" {
  description = "The Azure region for the resources."
  type        = string
}
variable "name_prefix" {
  description = "Prefix for resource names."
  type        = string
}
variable "resource_tags" {
  description = "Tags to apply to resources."
  type        = map(string)
}
variable "enable_entra_id" {
  description = "Enable Microsoft Entra ID authentication."
  type        = bool
}
variable "aad_tenant_id" {
  description = "Tenant ID for Entra authentication."
  type        = string
}
variable "deploying_principal_object_id" {
  description = "Object ID of the principal deploying the infrastructure."
  type        = string
}
variable "deploy_azure_openai" {
  description = "Deploy Azure OpenAI account."
  type        = bool
}
variable "sku" {
  description = "SKU for the App Service Plan."
  type        = string
  default     = "P0v3"
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
variable "enable_private_networking" {
  description = "If value is true, public networking will be disabled and private endpoints will be created for Azure Storage and Azure OpenAI."
  type        = bool
  default     = false
}
# only needed if enable_private_networking is true
variable "subnet_id" {
  description = "Subnet ID for private endpoints (required if enable_private_networking is true)."
  type        = string
  default     = null
  nullable    = true
}

variable "prompt_template" {
  description = "Prompt template content for the 'prompt-template' Key Vault secret."
  type        = string
  default     = "You are a medical documentation assistant supporting clinicians. Return well-structured German text, preserve clinical accuracy, and never invent data."
}

output "webapp_url" {
  description = "The URL of the backend web app."
  value       = "https://${azurerm_linux_web_app.main.default_hostname}"
}
output "web_app_name" {
  description = "The name of the backend web app."
  value       = azurerm_linux_web_app.main.name
}
output "storage_account_name" {
  description = "The name of the storage account."
  value       = azurerm_storage_account.main.name
}
output "storage_account_id" {
  description = "The ID of the storage account."
  value       = azurerm_storage_account.main.id
}
output "archive_file" {
  value = data.archive_file.webapp.output_sha
}
output "zip_output_path" {
  value = data.archive_file.webapp.output_path
}
output "entra_app_url" {
  value = "https://portal.azure.com/#view/Microsoft_AAD_IAM/ManagedAppMenuBlade/~/Users/objectId/${azuread_service_principal.this.object_id}/appId/${azuread_application.this.client_id}"
}

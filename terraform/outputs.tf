output "webapp_url" {
  value       = module.workload.webapp_url
  description = "The URL of the backend web app."
}
output "entra_app_url" {
  value       = module.workload.entra_app_url
  description = "The URL of the Enterprise Application to assign users to groups"
}

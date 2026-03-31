# --------------------------------------------------
# Lokale App zippen
# --------------------------------------------------

data "archive_file" "webapp" {
  type        = "zip"
  source_dir  = "upload/webapp"
  output_path = "upload/webapp.zip"
}

######################################################################################################
# Create files
resource "local_file" "webapp_runtime_config" {
  content = templatefile(
    "upload/webapp/runtime.config.json.tmpl",
    {
      webapp_url = "https://${azurerm_linux_web_app.main.default_hostname}"
      location   = var.location
    }
  )
  filename = "upload/webapp/runtime.config.json"
}
